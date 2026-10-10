# Task 4 Implementation Report: Starter Kit Local Arena & Replay Visualizer Integration

## Executive Summary
Task 4 integrated rule variant support into the standalone Bot Starter Kit and Web Replay Visualizer. Developers can now simulate, benchmark, and debug custom bots offline under standard and inverted RPS rule variants (`--variant inverted_rps`). The web replay UI now clearly highlights matches contested under `inverted_rps` with a dedicated badge and turn banner indicator.

## Changes Implemented

1. **Starter Kit Local Arena (`starter_kit/local_arena.py`)**:
   - Added `--variant` CLI argument via `argparse` with choices `["standard", "inverted_rps"]` (default: `"standard"`).
   - Updated `play_match` signature with `variant: str = "standard"` and passed `variant` into `GameState(max_turns=max_turns, variant=variant)`.
   - Updated `run_arena` to accept `variant: str = "standard"`, display `Rule Variant: {variant}` in tournament headers, output active rule variant in the tournament summary, and propagate `variant` to `play_match`.

2. **Starter Kit Documentation (`starter_kit/README.md`)**:
   - Added command line usage example for testing inverted combat offline in Section 1 (Quick Start):
     `python starter_kit/local_arena.py starter_kit/bot_template.py starter_kit/heuristic_bot.py --variant inverted_rps`.
   - Documented the mechanics of the `inverted_rps` rule variant (Scissors > Rock > Paper) in Section 2 (Game Rules & Mechanics).
   - Updated CLI options documentation table in Section 5 (Local Arena CLI Reference) to document `--variant {standard,inverted_rps}`.

3. **Web Replay Route (`server/main.py`)**:
   - Updated `replay_page` handler to query the `Match` record from SQLite by `match_id` and pass `"match": match` into the Jinja2 template context.

4. **Web Replay Template (`web/templates/replay.html`)**:
   - Rendered rule variant badge in the match information box:
     `{% if match and match.rule_variant == 'inverted_rps' %}` displaying `Chế độ: Đảo chiều ngũ hành (Kéo > Búa > Bao)`.
   - Included a hidden `#ruleVariantBadge` container for standard matches that can be dynamically updated if client-side API reports an inverted variant.
   - Updated client-side fetch logic in DOMContentLoaded listener to inspect `m.rule_variant` and display the badge if applicable.

5. **Replay Visualizer Client (`web/static/js/visualizer.js`)**:
   - Updated `loadReplay(data)` to inspect `data.rule_variant === 'inverted_rps'` and ensure `#ruleVariantBadge` is displayed and populated.
   - Updated `updateBanners(turn)` to append ` [Đảo chiều RPS]` to active turn banner messages and finished match summary when `rule_variant === 'inverted_rps'`.

6. **Design Tokens & CSS Styles (`web/static/css/style.css`)**:
   - Added `.tag.purple` design token styling for variant badges (`background: rgba(187, 134, 252, 0.15); color: #bb86fc; border: 1px solid rgba(187, 134, 252, 0.4);`).
   - Added `.variant-badge` flex container styling aligning with the Minimalist Slate/Charcoal palette.

7. **Automated Tests (`tests/test_starter_kit.py`, `tests/test_web.py`)**:
   - `test_local_arena_cli_with_variant`: Confirmed `local_arena.py --variant inverted_rps` runs successfully with exit code 0 and logs the rule variant.
   - `test_local_arena_play_match_variant`: Confirmed `play_match` accepts `variant="inverted_rps"` and runs simulated games without errors.
   - `test_readme_contains_rule_variant_instructions`: Confirmed `README.md` documents `--variant` and `inverted_rps`.
   - `test_replay_page_renders_variant_badge_for_inverted_rps`: Confirmed `/replay/{match_id}` renders `Đảo chiều ngũ hành (Kéo > Búa > Bao)` and `#ruleVariantBadge` when `match.rule_variant == 'inverted_rps'`.

## Test Verification
- **TDD Red Phase**: Ran `pytest tests/test_starter_kit.py tests/test_web.py -k "variant" -v`; verified 4 test failures as expected.
- **TDD Green Phase**: Ran `pytest tests/test_starter_kit.py tests/test_web.py -v`; verified all 33 tests passed.
- **Full Test Suite**: Ran `pytest -v`; all 353 tests passed with 0 regressions.

## Git Commit
- Hash: `7d9d694`
- Message: `feat(ui): add offline starter kit variant flag and replay badge`
