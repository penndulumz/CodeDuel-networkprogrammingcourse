# Task 4 Brief: Starter Kit Local Arena & Replay Visualizer Integration

## Objective
Enable offline CLI simulation of rule variants via `starter_kit/local_arena.py --variant <name>`, document this in `starter_kit/README.md`, and display a visual indicator/badge in the web replay page when a match is recorded under `inverted_rps`.

## Target Files
1. `tests/test_starter_kit.py`:
   - Add test verifying `local_arena.py --variant inverted_rps` runs successfully with exit code 0 and logs the rule variant.
2. `tests/test_web.py`:
   - Add test verifying that when a match has `rule_variant == "inverted_rps"`, visiting `/replay/{match_id}` displays the rule variant badge.
3. `starter_kit/local_arena.py`:
   - Add `--variant` argument to `argparse` (choices: `["standard", "inverted_rps"]`, default: `"standard"`).
   - In `play_match(...)`: add `variant: str = "standard"` parameter and instantiate `game = GameState(max_turns=max_turns, variant=variant)`.
   - In CLI summary output, display active rule variant (e.g. `print(f"Rule Variant: {args.variant}")`).
4. `starter_kit/README.md`:
   - Add explanation and usage example for testing rule variants offline:
     `python starter_kit/local_arena.py bot1.py bot2.py --variant inverted_rps`.
5. `web/templates/replay.html`:
   - In match information box, render variant badge if `match and match.rule_variant == 'inverted_rps'`:
     `Chế độ: Đảo chiều ngũ hành (Kéo > Búa > Bao)`.
6. `web/static/js/visualizer.js`:
   - When loading replay JSON data, if `data.rule_variant === 'inverted_rps'`, display variant indicator.

## Global Constraints
- Zero Node.js / npm dependencies. Pure Python 3.10+, Vanilla JS, HTML5/CSS3.
- Minimalist Slate/Charcoal palette.
- All code comments and docstrings in clear English.
- No decorative emojis in code, comments, or commit messages.
- Must pass `pytest tests/test_starter_kit.py tests/test_web.py -v`.
- Commit message: `feat(ui): add offline starter kit variant flag and replay badge`.
