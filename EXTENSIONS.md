## What extensions are good for

Extensions give you a safe place to add **measurement, experimentation, and tuning** to your miner without touching core SN33 code.

They’re useful when you want to:
- try different prompts, models, or response styles
- see what actually correlates with higher validator scores
- specialize behavior by task type
- optimize latency without guessing
- adapt when validator incentives change

Instead of baking assumptions into core logic, extensions let you layer these ideas on top — and remove them just as easily if they don’t work.

If an extension isn’t present, nothing breaks.
If core code upgrades, your extensions stay isolated.

---

# SN33 User Extensions (Plugins)

Extensions let miners and validators add custom functionality **without forking core code**.

The goal is to make experimentation safe:
- Drop an extension into `conversationgenome/extensions/`
- Upgrade core normally
- Your custom logic stays isolated and optional
- If an extension isn’t installed, calls are **no-ops** (non-breaking)

---

## Ways to use extensions to improve monetization

Extensions give you room to experiment and adjust your miner without committing to permanent changes.

Some common ways miners can use them:

- **Try multiple approaches safely**  
  Test different prompts, response formats, or models side-by-side instead of guessing which one works best.

- **Measure instead of assuming**  
  Track things like latency, output length, or response structure so you can see what changes when scores go up or down.

- **Tune behavior by task type**  
  Use different defaults for different tasks instead of forcing everything through the same response path.

- **Balance speed and quality intentionally**  
  Experiment with faster responses, truncation, or simpler reasoning paths when latency matters more than depth.

- **Adapt over time**  
  When scoring patterns change, extensions let you adjust quickly without rewriting core logic.

None of these require forking the codebase, and any experiment can be removed if it doesn’t help.

---

## Why miners should care (monetization + survivability)

Validators reward behavior that can drift over time. Extensions let you **measure and adapt** quickly without risky core edits.

High-ROI extension ideas:
- **A/B testing**: prompts, models, output formats, truncation strategies
- **Attribution / correlation**: latency vs score, verbosity vs score, style markers vs score
- **Latency profiling**: identify bottlenecks and enforce latency budgets
- **Task-type policies**: specialized behavior per task type without custom forks
- **Bandits / auto-tuners**: allocate more traffic to higher-scoring strategies

Extensions are a way to turn your miner from “one size fits all” into “adaptive specialist” with minimal upgrade risk.

---

## High-value extension categories

| Category | What it does | Why it matters |
|--------|--------------|----------------|
| A/B testing | Compare prompts, models, truncation strategies | Finds what validators actually reward |
| Attribution / correlation | Relate score to latency, verbosity, style | Turns black-box scoring into signal |
| Latency profiling | Measure end-to-end and step latency | Faster acceptable answers often win |
| Task-type policies | Different behavior per task type | One-size-fits-all is dominated |
| Model routing | Choose models per request | Cost and quality optimization |
| Bandits / auto-tuners | Auto-allocate traffic to winners | Continuous optimization |

Extensions can be private, shared, or eventually merged into core.

---

## Using extensions for task-specific behavior

SN33 supports different task types, and it’s often useful to handle them differently.

Extensions give you a way to:
- apply different prompts or models per task type
- adjust verbosity, latency targets, or output structure
- experiment with task-specific behavior without hardcoding it

This lets you avoid two common pitfalls:
- treating all tasks the same, even when they behave differently
- writing brittle, task-specific logic directly into core code

With extensions, task-specific ideas can live on the side and evolve independently.

---

## Design objectives

This extension system is intentionally simple.

It’s designed to:
- make it easy to add or remove custom behavior
- keep core code stable and upgradeable
- avoid tight coupling between extensions and internals
- fail safely when extensions are missing or misbehave

There are no required base classes, frameworks, or registration steps.
Extensions are plain Python files that can be added or removed as needed.




## Quickstart

### 1) Create an extension file

Create an extension file:

`conversationgenome/extensions/Example.py`

It should define a class with the same name as the file (`Example`) and any methods you want to call.

Example:

```python
class Example:
    def incStat(self, params):
        # params is always a dict
        metricName = params.get("metricName")
        inc = params.get("inc", 1)
        # do something with metricName/inc
        return True
```

### 2) Call extensions safely from anywhere

```python
from conversationgenome.extensions.Extensions import Extensions

ext = Extensions()
ext.execute("Example", "incStat", {"metricName": "windowsProcessed", "inc": 1})
```

If `Example` (or `incStat`) doesn’t exist, `execute()` returns `None` and your miner continues normally.

---

## Minimal contract

- Extensions are optional.
- Each extension method receives a single `params` dict.
- Extension call failures never crash the miner/validator loop; errors are logged.

---

## Latency timing hook (pseudo-code)

The idea: measure end-to-end latency (or step latency) and emit a metric.

```python
# core code
start = nowMs()

# ... do work ...

elapsedMs = nowMs() - start
ext.execute("Profiler", "observeLatency", {
    "event": "miner.handleWindow",
    "elapsedMs": elapsedMs,
    "taskType": window.get("taskType"),
    "validatorUid": request.get("validatorUid"),
})
```

And the extension:

```python
# conversationgenome/extensions/Profiler.py
class Profiler:
    def observeLatency(self, params):
        event = params["event"]
        elapsedMs = params["elapsedMs"]
        # Example: bucketize, log, or export to Prometheus / wandb
        # Keep it lightweight: no heavy storage, aggregate counters/histograms
        return True
```

---

## Notes for extension authors

- Keep extensions lightweight and failure-tolerant.
- Prefer aggregation (counts, histograms) over storing raw payloads.
- Treat extensions as “strategy/instrumentation modules” you can swap without touching core.



