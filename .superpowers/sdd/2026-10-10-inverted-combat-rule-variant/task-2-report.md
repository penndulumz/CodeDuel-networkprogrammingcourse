# Task 2 Implementation Report: Database Schema & Background Queue Variant Execution

## Overview
Implemented rule variant database persistence on the `Match` model and integrated active variant execution into `engine/runner.py` and `server/queue.py`. Matches now persist their combat variant, replays record the active rule variant, and match execution dynamically respects tournament database settings and explicit match configuration overrides with full backward compatibility defaulting to standard RPS rules.

## Changes Implemented

### 1. `server/models.py`
- Added column to `Match` model:
  ```python
  rule_variant: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)
  ```
- Ensures each match outcome permanently records whether it was played under standard or inverted rules.

### 2. `engine/runner.py`
- Added `variant: str = "standard"` parameter to `run_match(...)`.
- Instantiated game state with variant:
  ```python
  game = GameState(board=initial_board, turn=1, move_no=1, max_turns=max_turns, variant=variant)
  ```
- Updated `_format_match_result` to accept `variant: str = "standard"` and embed `"rule_variant": variant` into match outcome dictionaries and replay JSON structures across all execution exit paths.

### 3. `server/queue.py`
- Updated `execute_match_job` to determine the active rule variant:
  ```python
  db_variant = _get_setting_value(db, "rule_variant", None, str)
  match_variant = getattr(match, "rule_variant", None)
  if match_variant and match_variant != "standard":
      rule_variant = match_variant
  elif db_variant:
      rule_variant = db_variant
  else:
      rule_variant = match_variant or "standard"

  if not rule_variant:
      rule_variant = "standard"
  ```
- Passed `variant=rule_variant` to `run_match`.
- Recorded `match.rule_variant = rule_variant` to database alongside winner and replay path before commit.

### 4. `tests/test_queue.py`
Added unit and integration test coverage:
- `test_execute_match_job_honors_configured_rule_variant`: Verifies configured tournament setting `rule_variant="inverted_rps"` executes `run_match` with `variant="inverted_rps"` and commits `match.rule_variant == "inverted_rps"`.
- `test_execute_match_job_explicit_match_rule_variant_takes_precedence`: Verifies explicit `match.rule_variant` overrides tournament defaults.
- `test_execute_match_job_default_rule_variant_fallback`: Verifies matches default cleanly to `"standard"` when no setting is configured.
- `test_runner_executes_with_rule_variant`: Verifies `run_match` executes directly with rule variant and records it in result payload.

## TDD Verification
1. **Red Phase**: Executed `pytest tests/test_queue.py -k "rule_variant" -v`. Confirmed 3 failures on missing column and missing variant parameters.
2. **Green Phase**: Implemented changes in `server/models.py`, `engine/runner.py`, and `server/queue.py`.
3. **Queue Test Suite**: Executed `pytest tests/test_queue.py -v`: 12 passed in 0.71s.
4. **Game Variants Test Suite**: Executed `pytest tests/test_game_variants.py -v`: 9 passed in 0.04s.
5. **Full Repository Regression**: Executed `pytest -v`: 346 passed in 13.14s.

## Git Commit
- **Commit Hash**: `db23d4f`
- **Commit Title**: `feat(queue): persist and execute matches under configured rule variant`
- **Files**: `server/models.py`, `engine/runner.py`, `server/queue.py`, `tests/test_queue.py`
