# SN33 User Extensions (Plugins)

## Table of Contents
- [What extensions are good for](#what-extensions-are-good-for)
- [Ways to use extensions to improve monetization](#ways-to-use-extensions-to-improve-monetization)
- [Why miners should care](#why-miners-should-care-monetization--survivability)
- [High-value extension categories](#high-value-extension-categories)
- [Using extensions for task-specific behavior](#using-extensions-for-task-specific-behavior)
- [Design objectives](#design-objectives)
- [Quickstart](#quickstart)
- [Minimal contract](#minimal-contract)
- [Pseudo-code implementations](#pseudo-code-implementations)
  - [A/B testing](#ab-testing)
  - [Attribution / correlation](#attribution--correlation)
  - [Latency profiling](#latency-profiling)
  - [Task-specific behavior](#task-specific-behavior)
  - [Model routing](#model-routing)
  - [Bandits / auto-tuners](#bandits--auto-tuners)

---

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

## Ways to use extensions to improve monetization

Extensions give you room to experiment and adjust your miner without committing to permanent changes.

Some common ways miners can use them:

- **Try multiple approaches safely**  
  Test different prompts, response formats, or models side-by-side instead of guessing.

- **Measure instead of assuming**  
  Track latency, output size, or structure and see what changes when scores move.

- **Tune behavior by task type**  
  Use different defaults per task instead of forcing everything through one path.

- **Balance speed and quality intentionally**  
  Experiment with truncation or faster paths when latency matters more than depth.

- **Adapt over time**  
  Adjust quickly when scoring patterns shift, without rewriting core logic.

---

## Why miners should care (monetization + survivability)

Extensions make it easier to experiment without risking miner stability.

They allow you to:
- test ideas without maintaining a fork
- roll back changes that don’t help
- keep custom logic isolated from core upgrades

Over time, this makes your miner easier to maintain and easier to adapt.

---

## High-value extension categories

| Category | What it does | Why it matters |
|--------|--------------|----------------|
| A/B testing | Compare prompts or models | Finds what works instead of guessing |
| Attribution / correlation | Relate score to latency or structure | Turns outcomes into signal |
| Latency profiling | Measure response timing | Speed often matters |
| Task-type policies | Different behavior per task | Avoids one-size-fits-all |
| Model routing | Choose model per request | Cost / quality tradeoffs |
| Bandits / auto-tuners | Shift traffic to winners | Continuous adaptation |

---

## Using extensions for task-specific behavior

SN33 supports different task types, and it’s often useful to handle them differently.

Extensions give you a way to:
- apply different prompts or models per task
- adjust verbosity or latency targets
- experiment without hardcoding task logic

Task-specific ideas can live on the side and evolve independently.

---

## Design objectives

This extension system is intentionally simple.

It aims to:
- make it easy to add or remove custom behavior
- keep core code stable and upgradeable
- avoid tight coupling between extensions and internals
- fail safely when extensions are missing or misbehave

Extensions are plain Python files that can be added or removed as needed.

---

## Quickstart

### 1) Create an extension file

`conversationgenome/extensions/Example.py`

```python
class Example:
    def incStat(self, params):
        metricName = params.get("metricName")
        inc = params.get("inc", 1)
        return True
```

### 2) Call extensions safely

```python
from conversationgenome.extensions.Extensions import Extensions

ext = Extensions()
ext.execute("Example", "incStat", {"metricName": "windowsProcessed", "inc": 1})
```

---

## Minimal contract

- Extensions are optional.
- Each extension method receives a single `params` dict.
- Extension failures never crash the miner or validator.

---

## Pseudo-code implementations

### A/B testing

```python
variant = ext.execute("Experiment", "pickVariant", {"taskType": taskType}) or "A"
response = runVariant(variant, window)
ext.execute("Experiment", "recordOutcome", {"variant": variant, "score": score})
```

### Attribution / correlation

```python
ext.execute("Attribution", "observe", {
    "latencyMs": latencyMs,
    "outputSize": len(output),
    "score": score,
})
```

### Latency profiling

```python
t0 = nowMs()
handleWindow()
elapsed = nowMs() - t0
ext.execute("Profiler", "observeLatency", {"elapsedMs": elapsed})
```

### Task-specific behavior

```python
profile = ext.execute("TaskPolicy", "selectProfile", {"taskType": taskType}) or defaultProfile
runModel(profile, window)
```

### Model routing

```python
model = ext.execute("ModelRouter", "chooseModel", {"taskType": taskType}) or "default"
runModel(model, window)
```

### Bandits / auto-tuners

```python
choice = ext.execute("Bandit", "choose", {"context": taskType}) or "A"
reward = runChoice(choice)
ext.execute("Bandit", "update", {"choice": choice, "reward": reward})
```
