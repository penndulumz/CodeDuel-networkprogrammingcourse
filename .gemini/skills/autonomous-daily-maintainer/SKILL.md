---
name: autonomous-daily-maintainer
description: Use when running automated maintenance, continuous upgrades, regression testing, or autonomous feature development on the Battlecode RPS Platform using the Superpowers skill lifecycle
---

# Autonomous Daily Maintainer

## Overview
Synthesizes and invokes the entire **Superpowers skill lifecycle** (`using-superpowers`, `systematic-debugging`, `test-driven-development`, `brainstorming`, `writing-plans`, `subagent-driven-development`, `verification-before-completion`, `finishing-a-development-branch`) for non-interactive, autonomous maintenance and platform upgrades.

## When to Use
- Triggered on a daily schedule or manual prompt to maintain and evolve the Battlecode platform.
- When unattended bug detection, regression patching, bot tactical balancing, or continuous feature enhancement is requested.

---

## The Superpowers Autonomous Lifecycle Pipeline

```mermaid
flowchart TD
    Start["Trigger Daily Run"] --> Check["1. Regression Suite (pytest -v)"]
    Check -->|Tests Fail| Debug["Invoke superpowers:systematic-debugging"]
    Debug --> TDD["Invoke superpowers:test-driven-development"]
    TDD --> VerifyFix["Invoke superpowers:verification-before-completion"]
    VerifyFix --> Check

    Check -->|Tests Pass (100% Green)| Benchmark["2. Bot Arena Benchmark (starter_kit/local_arena.py)"]
    Benchmark --> Decision{"Needs Upgrade / Feature?"}
    
    Decision -->|Routine Maintenance| Schedule["3. Advance Tournament State (config/tournament.yaml)"]
    Schedule --> Report["4. Daily Health Report (docs/logs/)"]
    Report --> Commit["5. Commit Clean State"]

    Decision -->|Enhancement / Upgrade| Brainstorm["Invoke superpowers:brainstorming"]
    Brainstorm --> Plan["Invoke superpowers:writing-plans"]
    Plan --> SDD["Invoke superpowers:subagent-driven-development"]
    SDD --> LoopLaw["Enforce Continuous Feedback Loop Law (Update docs/CONTEXT_RESUME.md)"]
    LoopLaw --> Finish["Invoke superpowers:finishing-a-development-branch"]
    Finish --> Commit
```

---

## Detailed Execution Steps

### Phase 1: Automated Health Audit & Systematic Debugging
1. **Execute full test suite**:
   ```bash
   pytest -v
   ```
2. **If ANY test fails or bug is detected**:
   - **MUST INVOKE** `superpowers:systematic-debugging`:
     - Reproduce with minimal command.
     - Inspect exact stack traces and isolate root cause.
     - Formulate testable hypothesis before touching code.
   - **MUST INVOKE** `superpowers:test-driven-development`:
     - Write failing test reproducing the issue.
     - Verify test fails.
     - Implement minimal code fix.
     - Verify test passes.
   - **MUST INVOKE** `superpowers:verification-before-completion`:
     - Re-run full test suite (`pytest -v`) to confirm zero regressions.

### Phase 2: Bot Balance & Tactical Benchmarking
Run 10 head-to-head rounds between standard bots:
```bash
python starter_kit/local_arena.py starter_kit/bot_template.py starter_kit/heuristic_bot.py --rounds 10 --max-turns 150
```
Log victory ratios, average turns, and wipeout vs goal win distributions.

### Phase 3: Autonomous System Upgrades & Enhancements
When upgrading features (e.g. runner latency optimizations, new heuristic bot variants, tournament analytics):
1. **MUST INVOKE** `superpowers:brainstorming`:
   - Explore requirements and propose architectural approaches.
2. **MUST INVOKE** `superpowers:writing-plans`:
   - Decompose into bite-sized TDD tasks with file paths and interfaces.
3. **MUST INVOKE** `superpowers:subagent-driven-development`:
   - Dispatch implementer and reviewer subagents task-by-task.
4. **ENFORCE CONTINUOUS FEEDBACK LOOP LAW**:
   - If any API, schema, rule, or interface changed, **IMMEDIATELY UPDATE** `docs/CONTEXT_RESUME.md` and `TASKS.md` in the same commit.
5. **MUST INVOKE** `superpowers:finishing-a-development-branch`:
   - Merge back to `main` locally once all tests pass.

### Phase 4: Tournament State Maintenance & Reporting
1. Update `config/tournament.yaml` (daily Elo multiplier $x \in [1.2, 2.5]$, current day).
2. Generate health report at `docs/logs/daily_report_<YYYY-MM-DD>.md`.
3. Commit maintenance ledger:
   ```bash
   git add docs/logs/ config/tournament.yaml && git commit -m "chore(daily): autonomous maintenance and upgrade cycle <date>"
   ```
