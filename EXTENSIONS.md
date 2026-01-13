# SN33 User Extensions (Plugins)

Extensions let miners and validators add custom functionality **without forking core code**.

The goal is to make experimentation safe:
- Drop an extension into `conversationgenome/extensions/`
- Upgrade core normally
- Your custom logic stays isolated and optional
- If an extension isn’t installed, calls are **no-ops** (non-breaking)

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



