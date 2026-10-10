# Task 2 Brief: Database Schema & Background Queue Variant Execution

## Objective
Persist the tournament rule variant in `server/models.py` on the `Match` model, pass the active variant from database configuration into `engine/runner.py`'s `run_match`, and ensure `server/queue.py` executes and records matches with the appropriate `rule_variant`.

## Target Files
1. `tests/test_queue.py`: Add unit/integration tests verifying:
   - When `TournamentSetting(key="rule_variant", value="inverted_rps")` is configured, `execute_match_job` runs the match with `variant="inverted_rps"` and records `match.rule_variant == "inverted_rps"`.
   - When `match.rule_variant` is already explicitly set (e.g. "inverted_rps"), it takes precedence over default settings.
2. `server/models.py`:
   - In `Match`: Add column `rule_variant: Mapped[str] = mapped_column(String(32), default="standard", nullable=False)`.
3. `engine/runner.py`:
   - In `run_match(...)`: Add `variant: str = "standard"` parameter (default: `"standard"`).
   - In `run_match`, instantiate `game = GameState(board=initial_board, turn=1, move_no=1, max_turns=max_turns, variant=variant)`.
   - In `match_result`: Include `"rule_variant": variant`.
4. `server/queue.py`:
   - In `execute_match_job`:
     - Determine active variant: `rule_variant = getattr(match, "rule_variant", None) or _get_setting_value(db, "rule_variant", "standard", str)`. If `rule_variant` is empty or None, fallback to `"standard"`.
     - Pass `variant=rule_variant` to `run_match`.
     - Assign `match.rule_variant = rule_variant`.

## Global Constraints
- Zero Node.js / npm dependencies. Pure Python 3.10+.
- Backward compatibility: Matches default to `"standard"` if no setting or variant is provided.
- All code comments and docstrings in clear English.
- No decorative emojis in code, comments, or commit messages.
- Must pass `pytest tests/test_queue.py -v` and `pytest tests/test_game_variants.py -v`.
- Commit message: `feat(queue): persist and execute matches under configured rule variant`.
