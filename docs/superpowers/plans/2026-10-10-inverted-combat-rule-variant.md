# Inverted Combat Rule Variant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement dynamic tournament rule variant support with the Inverted Combat Cycle (`inverted_rps`: Scissors > Rock > Paper > Scissors) across game engine, runner, persistence, admin portal, replay visualizer, and offline starter kit.

**Architecture:** Extend core game engine with modular variant dispatching while maintaining default standard compatibility. Propagate active `rule_variant` setting from `TournamentSetting` into background execution queue and match records. Provide offline CLI testing via `starter_kit/local_arena.py --variant inverted_rps` and web management in the Admin portal.

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0 (SQLite WAL), Jinja2, HTML5/CSS3 (Charcoal design tokens), Vanilla JS.

**Spec:** `docs/superpowers/specs/2026-10-10-inverted-combat-rule-variant-design.md`

## Global Constraints
- Zero Node.js or npm runtime dependencies. Pure Python 3.10+, FastAPI, SQLite WAL, HTML5, CSS3, Vanilla JS.
- Backward Compatibility: Default behavior is strictly `standard` across all existing matches, tests, and endpoints.
- Slate/Charcoal palette (`#0d1117`, `#161b22`, `#30363d`, `#f0f6fc`, `#8b949e`).
- All code comments and docstrings in clear English.
- No decorative emojis or icons in documentation, code comments, or commit messages.
- Continuous Feedback Loop Law: Changes must be synchronized with `docs/CONTEXT_RESUME.md` and `TASKS.md`.
- Test-Driven Development (TDD): Write failing tests before implementation for each task.

## Review Focus
1. Invalid Combat Captures: Verify that under `inverted_rps`, Rock attempting to capture Scissors is rejected as an invalid move, while Scissors capturing Rock is permitted.
2. Legal Move Generation: Verify that `generate_legal_moves` accurately enumerates captures based on the active variant.
3. Queue Setting Inheritance: Verify that matches created when `TournamentSetting.rule_variant == "inverted_rps"` correctly inherit and execute under the inverted variant.
4. Admin Setting Persistence: Verify that updating `rule_variant` via `/api/admin/settings` rejects unsupported variant identifiers (HTTP 422/400).
5. Offline Starter Kit Isolation: Verify that `starter_kit/local_arena.py --variant inverted_rps` runs fully offline without requiring server or network dependencies.

---

### Task 1: Engine Layer Rule Variant Support

**Files:**
- Modify: `engine/game.py`
- Create: `tests/test_game_variants.py`

**Interfaces:**
- Produces:
  - `RULE_VARIANT_STANDARD = "standard"`
  - `RULE_VARIANT_INVERTED_RPS = "inverted_rps"`
  - `SUPPORTED_RULE_VARIANTS = ["standard", "inverted_rps"]`
  - `beats(a: str, b: str, variant: str = RULE_VARIANT_STANDARD) -> bool`
  - `is_valid_move(board, move, player, variant: str = RULE_VARIANT_STANDARD) -> bool`
  - `make_move(board, move, player, variant: str = RULE_VARIANT_STANDARD) -> tuple[board, move_dict]`
  - `generate_legal_moves(board, player, variant: str = RULE_VARIANT_STANDARD) -> list[move_dict]`
  - `Game(variant: str = RULE_VARIANT_STANDARD)`

- [ ] **Step 1: Write failing tests in `tests/test_game_variants.py`**

```python
def test_beats_standard_vs_inverted():
    # Verify standard: R > S, S > P, P > R
    # Verify inverted: S > R, R > P, P > S
    ...

def test_is_valid_move_combat_inverted():
    # Verify Scissors capturing Rock is legal under inverted, illegal under standard
    ...

def test_game_class_variant_lifecycle():
    # Verify Game(variant="inverted_rps") clones properly and records rule_variant in export_history()
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_game_variants.py -v`
Expected: FAIL (argument variant unexpected or test file missing)

- [ ] **Step 3: Implement variant logic in `engine/game.py`**

Add constants, update `beats`, `is_valid_move`, `make_move`, `generate_legal_moves`, and `Game` constructor / serialization methods.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_game_variants.py tests/test_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add engine/game.py tests/test_game_variants.py
git commit -m "feat(engine): add rule variant support with inverted combat cycle"
```

---

### Task 2: Database Schema & Background Queue Variant Execution

**Files:**
- Modify: `server/models.py`
- Modify: `engine/runner.py`
- Modify: `server/queue.py`
- Modify: `tests/test_queue.py`

**Interfaces:**
- Consumes: `engine.game.Game(variant=...)`, `SUPPORTED_RULE_VARIANTS`
- Produces:
  - `Match.rule_variant: Column(String(32))`
  - `TournamentSetting.rule_variant: Column(String(32))`
  - `GameRunner.play_match(..., variant: str = "standard")`
  - Queue worker reads `TournamentSetting.rule_variant` and saves into `Match.rule_variant`

- [ ] **Step 1: Write failing tests in `tests/test_queue.py`**

```python
def test_queue_processes_match_with_inverted_rule_variant(clean_db):
    # Set TournamentSetting.rule_variant = "inverted_rps"
    # Queue match, run process_next_match
    # Assert completed match has rule_variant == "inverted_rps"
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_queue.py::test_queue_processes_match_with_inverted_rule_variant -v`
Expected: FAIL (attribute or column rule_variant missing)

- [ ] **Step 3: Update `server/models.py`, `engine/runner.py`, and `server/queue.py`**

Add `rule_variant` to `Match` and `TournamentSetting`. Pass `variant` through `runner.play_match` to `Game(variant=variant)`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_queue.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/models.py engine/runner.py server/queue.py tests/test_queue.py
git commit -m "feat(queue): persist and execute matches under configured rule variant"
```

---

### Task 3: Admin Web Management & Tournament API Integration

**Files:**
- Modify: `server/routes/admin.py`
- Modify: `server/routes/matches.py`
- Modify: `web/templates/admin.html`
- Modify: `tests/test_admin_schedule.py`

**Interfaces:**
- Consumes: `TournamentSetting.rule_variant`
- Produces:
  - `TournamentSettingUpdate.rule_variant: Optional[str]`
  - Admin UI dropdown for `rule_variant`
  - `POST /api/matches/challenge` sets `match.rule_variant` from `TournamentSetting`

- [ ] **Step 1: Write failing tests in `tests/test_admin_schedule.py`**

```python
def test_admin_update_rule_variant():
    # POST /api/admin/settings with rule_variant="inverted_rps"
    # Assert DB persists inverted_rps
    # POST with invalid variant returns 422 or 400
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_admin_schedule.py::test_admin_update_rule_variant -v`
Expected: FAIL

- [ ] **Step 3: Update `server/routes/admin.py`, `server/routes/matches.py`, and `web/templates/admin.html`**

Add `rule_variant` validation to `TournamentSettingUpdate`. Add selector to `admin.html`. Ensure challenge creation copies active variant.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_admin_schedule.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/routes/admin.py server/routes/matches.py web/templates/admin.html tests/test_admin_schedule.py
git commit -m "feat(admin): add dynamic rule variant configuration to admin portal"
```

---

### Task 4: Starter Kit Local Arena & Replay Visualizer Integration

**Files:**
- Modify: `starter_kit/local_arena.py`
- Modify: `starter_kit/README.md`
- Modify: `web/templates/replay.html`
- Modify: `web/static/js/visualizer.js`
- Modify: `tests/test_starter_kit.py`
- Modify: `tests/test_web.py`

**Interfaces:**
- Consumes: `engine.game.Game(variant=...)`, `match.rule_variant`
- Produces:
  - CLI flag `--variant` in `starter_kit/local_arena.py`
  - Replay visualizer badge for inverted combat

- [ ] **Step 1: Write failing tests in `tests/test_starter_kit.py` and `tests/test_web.py`**

```python
def test_local_arena_supports_variant_flag():
    # Run local_arena.py with --variant inverted_rps --max-turns 5
    # Assert exit code 0 and output mentions inverted_rps
    ...

def test_replay_template_renders_rule_variant_badge():
    # Load replay page of an inverted_rps match
    # Assert page displays rule variant indicator
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_starter_kit.py::test_local_arena_supports_variant_flag -v`
Expected: FAIL

- [ ] **Step 3: Update `starter_kit/local_arena.py`, `replay.html`, and `visualizer.js`**

Implement `--variant` CLI parser and pass into `Game(variant=args.variant)`. Render variant badge in replay transport banner.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_starter_kit.py tests/test_web.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add starter_kit/local_arena.py starter_kit/README.md web/templates/replay.html web/static/js/visualizer.js tests/test_starter_kit.py tests/test_web.py
git commit -m "feat(ui): add offline starter kit variant flag and replay badge"
```

---

### Task 5: Documentation Harmonization & Continuous Feedback Loop

**Files:**
- Modify: `docs/CONTEXT_RESUME.md`
- Modify: `TASKS.md`
- Modify: `README.md`
- Modify: `tests/test_documentation_integrity.py`

**Interfaces:**
- Consumes: Documentation SSOT standards

- [ ] **Step 1: Write failing tests in `tests/test_documentation_integrity.py`**

```python
def test_context_resume_rule_variant_content():
    # Verify Section 17 in docs/CONTEXT_RESUME.md covers Inverted Combat (inverted_rps)
    ...

def test_tasks_milestone_11_content():
    # Verify Milestone 11 in TASKS.md documents all 5 variant tasks
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest tests/test_documentation_integrity.py -k "milestone_11 or rule_variant" -v`
Expected: FAIL

- [ ] **Step 3: Update `docs/CONTEXT_RESUME.md`, `TASKS.md`, and `README.md`**

Add Section 17 to `docs/CONTEXT_RESUME.md`. Add Milestone 11 to `TASKS.md`. Ensure 100% zero decorative emojis.

- [ ] **Step 4: Run full regression test suite**

Run: `pytest -q`
Expected: 100% PASS

- [ ] **Step 5: Commit**

```bash
git add docs/CONTEXT_RESUME.md TASKS.md README.md tests/test_documentation_integrity.py
git commit -m "docs: synchronize inverted combat rule variant architecture and milestone records"
```
