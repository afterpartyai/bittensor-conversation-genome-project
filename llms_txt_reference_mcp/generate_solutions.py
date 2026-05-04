"""Generate code solutions from an LLM (OpenAI or Anthropic), optionally
grounded by a local stdio-based MCP server that exposes documentation tools.

Built for the GitChameleon dataset (https://gitchameleon-2-0.github.io/) — a
benchmark of version-pinned Python coding tasks — but the input format is
generic enough that any JSONL dataset with the schema below will work.

Given a JSONL dataset of version-pinned coding tasks, for each example the
script prompts the model to emit a complete Python module. In `--mode with-mcp`
the model is given the MCP server's tools and may call them (in a loop,
bounded by `--max-iters`) before producing its final answer.

Install
-------
    # One of:
    pip install "openai>=1.0"       # for --llm-provider openai or openrouter
    pip install "anthropic>=0.40"   # for --llm-provider anthropic

    # Only if you plan to use --mode with-mcp:
    pip install "mcp>=1.0"

Auth
----
    - OpenAI:     OPENAI_API_KEY must be set in the environment.
    - Anthropic:  ANTHROPIC_API_KEY must be set in the environment.
    - OpenRouter: OPENROUTER_API_KEY must be set in the environment
                  (served via the openai SDK pointed at https://openrouter.ai/api/v1).

Usage
-----
    # OpenAI, no MCP:
    python generate_solutions.py \\
        --llm-provider openai --model gpt-5.4-nano \\
        --mode no-mcp \\
        --dataset dataset.jsonl --out solutions.jsonl

    # OpenAI, with MCP tools (server is launched as a stdio child process):
    python generate_solutions.py \\
        --llm-provider openai --model gpt-5.4-nano \\
        --mode with-mcp \\
        --dataset dataset.jsonl --out solutions.jsonl \\
        --mcp-server-path ./my_mcp_server.py

    # Anthropic, with MCP tools:
    python generate_solutions.py \\
        --llm-provider anthropic --model claude-sonnet-4-6 \\
        --mode with-mcp \\
        --dataset dataset.jsonl --out solutions.jsonl \\
        --mcp-server-path ./my_mcp_server.py

    # OpenRouter (model names use the 'vendor/model-id' format):
    python generate_solutions.py \\
        --llm-provider openrouter --model anthropic/claude-sonnet-4-6 \\
        --mode with-mcp \\
        --dataset dataset.jsonl --out solutions.jsonl \\
        --mcp-server-path ./my_mcp_server.py

Input dataset schema (one JSON object per line)
-----------------------------------------------
Matches the GitChameleon dataset format
(https://gitchameleon-2-0.github.io/):


    {
        "example_id":              <str or int>,   # unique per row
        "library":                 <str>,          # e.g. "numpy"
        "version":                 <str>,          # e.g. "1.24.0"
        "python_version":          <str>,          # e.g. "3.10"
        "additional_dependencies": <str | null>,   # free-text list, optional
        "problem":                 <str>,          # task description
        "starting_code":           <str>           # signature/imports to reproduce verbatim
    }

Output files
------------
Two JSONL files are written (both appended to, so re-runs resume where
they left off, skipping already-completed (example_id, iteration) pairs):

    <--out>                       one record per attempt:
        {"example_id": ..., "iteration": ..., "answer": <model output>}

    <--out stem>_stats.jsonl      one record per attempt:
        {"example_id": ..., "iteration": ..., "iterations": <LLM rounds>,
         "tool_calls": [ {name, args, duration_ms, ok, empty, error}, ... ]}

An aggregate MCP-usage summary is printed to stdout when the run finishes.
"""

import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any


def load_jsonl(path: str) -> list[dict]:
    """Load a JSONL file as a list of dicts (ignoring blank lines)."""
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


_FENCE_RE = re.compile(r"```(?:python|py)?\s*\n?(.*?)```", re.DOTALL)


def extract_code(text: str) -> str:
    """If `text` contains a ```python ...``` fenced block, return only its contents.

    Defensive: some models (notably Claude Haiku after MCP tool use) emit a short
    prose bridge like "Based on my knowledge…" before the code despite the system
    prompt. Stripping to the fence gives a valid .py module regardless.
    """
    match = _FENCE_RE.search(text)
    if match:
        return match.group(1).strip()
    return text

BASE_SYSTEM_PROMPT = (
    "You are a Python coding assistant. You will be given a function signature and a task "
    "description that must be solved using a specific pinned version of a Python library. "
    "Return a COMPLETE, runnable Python module: include every needed import, the full "
    "function definition (repeat the provided signature verbatim), and the implementation "
    "body. Your output will be written to a .py file and imported directly, so top-level "
    "code must be valid Python. Do not add explanations. A single ```python fenced block "
    "is acceptable; plain code is also acceptable."
)

MCP_SYSTEM_SUFFIX = (
    "\n\nYou have MCP tools available for looking up library documentation. The pinned "
    "library version is often OLD, and your internal knowledge of its API may be outdated "
    "or wrong. Before writing code, CALL the available tools to verify which functions, "
    "signatures, and behaviors exist in this exact version — especially for any non-trivial "
    "API (uncommon functions, recently renamed/removed symbols, version-specific flags). "
    "Prefer grounding your solution in tool-retrieved evidence over guessing from memory. "
    "Only skip tool use when the solution is entirely version-agnostic Python. Once you "
    "have enough evidence, stop calling tools and emit the final code. "
    "If the MCP returns links to documentation pages, you may follow them as needed.\n\n"
    "OUTPUT RULE: Your final message (the one with no tool calls) must contain ONLY the "
    "Python module — no preamble, no summary, no narration of what the tools returned. "
    "Do NOT start with phrases like 'Based on my knowledge', 'Based on the documentation', "
    "'I'll implement', 'Here is', or any other lead-in. Emit the code directly (optionally "
    "inside a single ```python fenced block) and stop."
)


def system_prompt(mode: str) -> str:
    return BASE_SYSTEM_PROMPT + (MCP_SYSTEM_SUFFIX if mode == "with-mcp" else "")

USER_TEMPLATE = """Library: {library}=={version}
Python: {python_version}
Additional dependencies: {additional_dependencies}

Task:
{problem}

Starting code (reproduce these lines exactly, then add the implementation):
{starting_code}
"""


def _user_content(ex: dict) -> str:
    return USER_TEMPLATE.format(
        library=ex["library"],
        version=ex["version"],
        python_version=ex["python_version"],
        additional_dependencies=ex.get("additional_dependencies") or "(none)",
        problem=ex["problem"],
        starting_code=ex["starting_code"],
    )


def build_messages(ex: dict, mode: str) -> list[dict]:
    """OpenAI-style message list with the system prompt as the first message."""
    return [
        {"role": "system", "content": system_prompt(mode)},
        {"role": "user", "content": _user_content(ex)},
    ]


def build_messages_anthropic(ex: dict, mode: str) -> tuple[str, list[dict]]:
    """Anthropic-style (system, messages) pair — system is a separate field, not a message."""
    return system_prompt(mode), [{"role": "user", "content": _user_content(ex)}]


async def list_mcp_tools(session, provider: str) -> list[dict]:
    """Convert MCP server tool declarations to the provider's native tool-spec format."""
    resp = await session.list_tools()
    if provider in ("openai", "openrouter"):
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema or {"type": "object", "properties": {}},
                },
            }
            for t in resp.tools
        ]
    # anthropic
    return [
        {
            "name": t.name,
            "description": t.description or "",
            "input_schema": t.inputSchema or {"type": "object", "properties": {}},
        }
        for t in resp.tools
    ]


def tool_result_to_text(result) -> tuple[str, bool]:
    """Flatten an MCP CallToolResult into (text, ok) for feeding back to the LLM."""
    parts = []
    for item in result.content:
        text = getattr(item, "text", None)
        parts.append(text if text is not None else str(item))
    return "\n".join(parts), not bool(result.isError)


def is_empty_result(text: str) -> bool:
    """True if the tool succeeded but returned no useful data (empty list,
    empty dict, or a lone {"error": "..."} not-found payload)."""
    stripped = text.strip()
    if not stripped:
        return True
    try:
        data = json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        return False
    if isinstance(data, (list, dict)) and not data:
        return True
    if isinstance(data, dict) and set(data.keys()) == {"error"}:
        return True
    return False


async def _solve_with_mcp_openai(
    client: Any,
    model: str,
    ex: dict,
    session,
    mcp_tools: list[dict],
    max_iters: int,
) -> tuple[str, dict]:
    messages: list = build_messages(ex, "with-mcp")
    stats: dict = {"example_id": ex["example_id"], "iterations": 0, "tool_calls": []}

    for _ in range(max_iters):
        stats["iterations"] += 1
        resp = await client.chat.completions.create(
            model=model,
            messages=messages,
            tools=mcp_tools,
        )
        msg = resp.choices[0].message
        if not msg.tool_calls:
            return extract_code(msg.content or ""), stats

        messages.append(msg)
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}

            t0 = time.perf_counter()
            empty = False
            try:
                result = await session.call_tool(name, args)
                text, ok = tool_result_to_text(result)
                empty = ok and is_empty_result(text)
            except Exception as e:
                text, ok = f"[exception] {type(e).__name__}: {e}", False
            dt_ms = (time.perf_counter() - t0) * 1000

            stats["tool_calls"].append(
                {
                    "name": name,
                    "args": args,
                    "duration_ms": round(dt_ms, 1),
                    "ok": ok,
                    "empty": empty,
                    "error": None if ok else text,
                }
            )
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": text})

    stats["error"] = "max_iters_reached"
    return "", stats


async def _solve_with_mcp_anthropic(
    client: Any,
    model: str,
    ex: dict,
    session,
    mcp_tools: list[dict],
    max_iters: int,
    max_tokens: int,
) -> tuple[str, dict]:
    system, messages = build_messages_anthropic(ex, "with-mcp")
    stats: dict = {"example_id": ex["example_id"], "iterations": 0, "tool_calls": []}

    # Prompt caching: both the system prompt and the tool list are identical across every
    # example in a run, so marking them ephemeral gives us cache hits from the second call on.
    system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    if mcp_tools:
        cached_tools = [*mcp_tools[:-1], {**mcp_tools[-1], "cache_control": {"type": "ephemeral"}}]
    else:
        cached_tools = mcp_tools

    for _ in range(max_iters):
        stats["iterations"] += 1
        resp = await client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_blocks,
            messages=messages,
            tools=cached_tools,
        )

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        text_blocks = [b for b in resp.content if getattr(b, "type", None) == "text"]

        if not tool_uses:
            final = "\n".join(b.text for b in text_blocks)
            return extract_code(final), stats

        messages.append({"role": "assistant", "content": [b.model_dump() for b in resp.content]})

        tool_result_blocks = []
        for tu in tool_uses:
            name = tu.name
            args = tu.input or {}

            t0 = time.perf_counter()
            empty = False
            try:
                result = await session.call_tool(name, args)
                text, ok = tool_result_to_text(result)
                empty = ok and is_empty_result(text)
            except Exception as e:
                text, ok = f"[exception] {type(e).__name__}: {e}", False
            dt_ms = (time.perf_counter() - t0) * 1000

            stats["tool_calls"].append(
                {
                    "name": name,
                    "args": args,
                    "duration_ms": round(dt_ms, 1),
                    "ok": ok,
                    "empty": empty,
                    "error": None if ok else text,
                }
            )
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tu.id,
                    "content": text,
                    "is_error": not ok,
                }
            )

        messages.append({"role": "user", "content": tool_result_blocks})

    stats["error"] = "max_iters_reached"
    return "", stats


async def solve_with_mcp(
    provider: str,
    client: Any,
    model: str,
    ex: dict,
    session,
    mcp_tools: list[dict],
    max_iters: int,
    max_tokens: int,
) -> tuple[str, dict]:
    """Run one LLM<->MCP tool-use loop for `ex` and return (final_answer, stats)."""
    if provider in ("openai", "openrouter"):
        return await _solve_with_mcp_openai(client, model, ex, session, mcp_tools, max_iters)
    return await _solve_with_mcp_anthropic(client, model, ex, session, mcp_tools, max_iters, max_tokens)


async def _solve_no_mcp_openai(client: Any, model: str, ex: dict) -> tuple[str, dict]:
    resp = await client.chat.completions.create(model=model, messages=build_messages(ex, "no-mcp"))
    return extract_code(resp.choices[0].message.content or ""), {
        "example_id": ex["example_id"],
        "iterations": 1,
        "tool_calls": [],
    }


async def _solve_no_mcp_anthropic(
    client: Any, model: str, ex: dict, max_tokens: int
) -> tuple[str, dict]:
    system, messages = build_messages_anthropic(ex, "no-mcp")
    resp = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    text = "\n".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return extract_code(text), {"example_id": ex["example_id"], "iterations": 1, "tool_calls": []}


async def solve_no_mcp(
    provider: str, client: Any, model: str, ex: dict, max_tokens: int
) -> tuple[str, dict]:
    """Single-shot model call for `ex`, no tools."""
    if provider in ("openai", "openrouter"):
        return await _solve_no_mcp_openai(client, model, ex)
    return await _solve_no_mcp_anthropic(client, model, ex, max_tokens)


def already_done(out_path: Path) -> set[tuple[str, int]]:
    """Return (example_id, iteration) pairs already written to `out_path`, so we can resume."""
    if not out_path.exists():
        return set()
    done: set[tuple[str, int]] = set()
    with out_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                done.add((rec["example_id"], rec.get("iteration", 0)))
            except (json.JSONDecodeError, KeyError):
                continue
    return done


def print_stats_summary(all_stats: list[dict]) -> None:
    """Print an aggregate tool-call / iteration summary over all attempts."""
    total = len(all_stats)
    used = [s for s in all_stats if s["tool_calls"]]
    all_calls = [c for s in all_stats for c in s["tool_calls"]]
    per_tool = Counter(c["name"] for c in all_calls)
    per_tool_empty = Counter(c["name"] for c in all_calls if c.get("empty"))
    errors = [c for c in all_calls if not c["ok"]]
    empties = [c for c in all_calls if c.get("empty")]

    print("\n--- MCP usage summary ---")
    print(f"Examples attempted:      {total}")
    print(f"Examples that used MCP:  {len(used)}")
    print(f"Total tool calls:        {len(all_calls)}")
    if all_calls:
        print(f"Tool-call success rate:  {100 * (1 - len(errors) / len(all_calls)):.1f}%")
        print(f"Empty (no-result) calls: {len(empties)} ({100 * len(empties) / len(all_calls):.1f}%)")
        print(f"Avg calls per using-ex:  {len(all_calls) / max(1, len(used)):.2f}")
        print(f"Avg LLM iterations/ex:   {sum(s['iterations'] for s in all_stats) / total:.2f}")
        print("Per-tool counts (empty / total):")
        for name, n in per_tool.most_common():
            print(f"  {name}: {per_tool_empty[name]} / {n}")
    if errors:
        print(f"Tool errors:             {len(errors)}")


async def run_no_mcp(provider, client, model, pending, out_path, stats_path, concurrency, max_tokens):
    """Fan out no-MCP solves across `concurrency` coroutines, appending results as they complete."""
    write_lock = asyncio.Lock()
    all_stats: list = []
    sem = asyncio.Semaphore(concurrency)

    async def one(ex, iteration, out_f, stats_f):
        async with sem:
            try:
                answer, stats = await solve_no_mcp(provider, client, model, ex, max_tokens)
            except Exception as e:
                print(f"  {ex['example_id']} (iter {iteration}) FAILED: {e}", file=sys.stderr)
                return
            stats["iteration"] = iteration
            async with write_lock:
                out_f.write(json.dumps({"example_id": ex["example_id"], "iteration": iteration, "answer": answer}) + "\n")
                out_f.flush()
                stats_f.write(json.dumps(stats) + "\n")
                stats_f.flush()
                all_stats.append(stats)
                print(f"  {ex['example_id']} (iter {iteration}) ok ({len(answer)} chars)")

    with out_path.open("a") as out_f, stats_path.open("a") as stats_f:
        await asyncio.gather(*(one(ex, it, out_f, stats_f) for ex, it in pending))
    return all_stats


async def run_with_mcp(provider, client, model, pending, out_path, stats_path, concurrency, mcp_params, max_iters, max_tokens):
    """Fan out with-MCP solves: each worker owns its own stdio MCP session and pulls work from a shared queue."""
    # Imported inside the function so `--mode no-mcp` doesn't require the `mcp` package.
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client

    write_lock = asyncio.Lock()
    all_stats: list = []

    queue: asyncio.Queue = asyncio.Queue()
    for ex, iteration in pending:
        queue.put_nowait((ex, iteration))

    async def worker(worker_id: int, out_f, stats_f):
        async with stdio_client(mcp_params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                tools = await list_mcp_tools(session, provider)
                if worker_id == 0:
                    names = [
                        t["function"]["name"] if provider in ("openai", "openrouter") else t["name"]
                        for t in tools
                    ]
                    print(f"MCP tools available: {names}")
                while True:
                    try:
                        ex, iteration = queue.get_nowait()
                    except asyncio.QueueEmpty:
                        return
                    try:
                        answer, stats = await solve_with_mcp(provider, client, model, ex, session, tools, max_iters, max_tokens)
                    except Exception as e:
                        print(f"  {ex['example_id']} (iter {iteration}) FAILED: {e}", file=sys.stderr)
                        continue
                    stats["iteration"] = iteration
                    async with write_lock:
                        out_f.write(json.dumps({"example_id": ex["example_id"], "iteration": iteration, "answer": answer}) + "\n")
                        out_f.flush()
                        stats_f.write(json.dumps(stats) + "\n")
                        stats_f.flush()
                        all_stats.append(stats)
                        n_calls = len(stats["tool_calls"])
                        print(f"  {ex['example_id']} (iter {iteration}) ok ({len(answer)} chars, {n_calls} tool calls)")

    with out_path.open("a") as out_f, stats_path.open("a") as stats_f:
        await asyncio.gather(*(worker(i, out_f, stats_f) for i in range(concurrency)))
    return all_stats


def main() -> None:
    """Parse CLI args and dispatch to the no-mcp / with-mcp runner."""
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--llm-provider",
        choices=["openai", "anthropic", "openrouter"],
        default="openai",
        help=(
            "Which LLM backend to use. 'openrouter' reuses the openai SDK against "
            "https://openrouter.ai/api/v1 and reads OPENROUTER_API_KEY."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=["with-mcp", "no-mcp"],
        required=True,
        help="Whether to expose MCP tools to the model.",
    )
    parser.add_argument(
        "--model",
        required=True,
        help=(
            "Model name passed through to the provider. Examples: 'gpt-4o-mini' (openai), "
            "'claude-sonnet-4-6' (anthropic), 'anthropic/claude-sonnet-4-6' (openrouter)."
        ),
    )
    parser.add_argument(
        "--dataset",
        required=True,
        help=(
            "Path to the input JSONL dataset. Built for GitChameleon "
            "(https://gitchameleon-2-0.github.io/); see module docstring for the expected schema."
        ),
    )
    parser.add_argument(
        "--out",
        required=True,
        type=Path,
        help="Path to the output solutions JSONL (appended to; a '_stats.jsonl' sidecar is written alongside).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process the first N examples from the dataset.",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=4,
        help="Number of examples processed in parallel (with-mcp: also the number of MCP sessions).",
    )
    parser.add_argument(
        "--max-iters",
        type=int,
        default=10,
        help="Max LLM<->MCP tool-use rounds per example (with-mcp mode only).",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=4096,
        help="Max completion tokens per model call. Required for Anthropic; ignored for OpenAI.",
    )
    parser.add_argument(
        "--num-iterations",
        type=int,
        default=1,
        help="Run the full dataset this many times; each attempt is tagged with an iteration index.",
    )
    parser.add_argument(
        "--mcp-server-path",
        type=Path,
        help="Path to the MCP server .py (required when --mode with-mcp).",
    )
    parser.add_argument(
        "--mcp-python",
        default=sys.executable,
        help="Python interpreter used to run the MCP server (default: current interpreter).",
    )
    args = parser.parse_args()

    examples = load_jsonl(str(args.dataset))
    if args.limit is not None:
        examples = examples[: args.limit]

    if args.num_iterations < 1:
        sys.exit("--num-iterations must be >= 1")

    done = already_done(args.out)
    pending = [
        (ex, it)
        for it in range(args.num_iterations)
        for ex in examples
        if (ex["example_id"], it) not in done
    ]
    print(
        f"{len(done)} already done, {len(pending)} to generate "
        f"({len(examples)} examples x {args.num_iterations} iterations), mode={args.mode}"
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    stats_path = args.out.with_name(args.out.stem + "_stats.jsonl")

    if args.llm_provider == "openai":
        from openai import AsyncOpenAI

        client: Any = AsyncOpenAI()
    elif args.llm_provider == "openrouter":
        from openai import AsyncOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            sys.exit("OPENROUTER_API_KEY must be set for --llm-provider openrouter")
        client = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
    else:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic()

    if args.mode == "no-mcp":
        all_stats = asyncio.run(
            run_no_mcp(
                args.llm_provider,
                client,
                args.model,
                pending,
                args.out,
                stats_path,
                args.concurrency,
                args.max_tokens,
            )
        )
    else:
        if not args.mcp_server_path:
            sys.exit("--mcp-server-path is required in with-mcp mode")
        server_path = args.mcp_server_path.resolve()
        if not server_path.is_file():
            sys.exit(f"MCP server not found: {server_path}")

        from mcp import StdioServerParameters

        mcp_params = StdioServerParameters(
            command=args.mcp_python,
            args=[str(server_path)],
            cwd=str(server_path.parent),
            env=os.environ.copy(),
        )
        all_stats = asyncio.run(
            run_with_mcp(
                args.llm_provider,
                client,
                args.model,
                pending,
                args.out,
                stats_path,
                args.concurrency,
                mcp_params,
                args.max_iters,
                args.max_tokens,
            )
        )

    print_stats_summary(all_stats)
    print(f"Per-example stats written to: {stats_path}")


if __name__ == "__main__":
    main()
