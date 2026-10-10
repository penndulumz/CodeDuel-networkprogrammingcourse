# Task 1 Brief: Engine Layer Rule Variant Support

## Objective
Implement rule variant support in `engine/game.py` supporting both standard RPS rules and the Inverted Combat Cycle (`inverted_rps`: Scissors beats Rock, Rock beats Paper, Paper beats Scissors).
Ensure complete backward compatibility so that passing no variant defaults to `standard`.

## Target Files
1. `tests/test_game_variants.py`: Create comprehensive unit tests verifying:
   - `beats(a, b, variant="standard")` vs `beats(a, b, variant="inverted_rps")`.
   - `is_valid_move` combat checks: under `inverted_rps`, Scissors captures Rock, Rock cannot capture Scissors.
   - `make_move` combat resolution under `inverted_rps`.
   - `generate_legal_moves` respects the active variant.
   - `Game(variant="inverted_rps")` lifecycle: `clone()`, `to_dict()`, and `export_history()` preserve `rule_variant`.
2. `engine/game.py`:
   - Define constants:
     - `RULE_VARIANT_STANDARD: str = "standard"`
     - `RULE_VARIANT_INVERTED_RPS: str = "inverted_rps"`
     - `SUPPORTED_RULE_VARIANTS: list[str] = [RULE_VARIANT_STANDARD, RULE_VARIANT_INVERTED_RPS]`
   - Update `beats(a: str, b: str, variant: str = RULE_VARIANT_STANDARD) -> bool`:
     - Under `inverted_rps`: `(a == 'S' and b == 'R') or (a == 'R' and b == 'P') or (a == 'P' and b == 'S')`.
     - Under `standard` (and fallback): `(a == 'R' and b == 'S') or (a == 'S' and b == 'P') or (a == 'P' and b == 'R')`.
   - Update `is_valid_move(board, move, player, variant: str = RULE_VARIANT_STANDARD) -> bool`:
     - When inspecting destination capture, pass `variant=variant` to `beats`.
   - Update `make_move(board, move, player, variant: str = RULE_VARIANT_STANDARD)`:
     - Pass `variant=variant` when checking capture legality and SAN generation.
   - Update `generate_legal_moves(board, player, variant: str = RULE_VARIANT_STANDARD)`:
     - Pass `variant=variant` to `is_valid_move`.
   - Update `Game` class:
     - `__init__(self, variant: str = RULE_VARIANT_STANDARD)`: store `self.variant = variant if variant in SUPPORTED_RULE_VARIANTS else RULE_VARIANT_STANDARD`.
     - In `is_valid_move`, `make_move`, `generate_legal_moves`: use `self.variant`.
     - In `clone()`: create new `Game(variant=self.variant)` and copy board/state.
     - In `to_dict()` and `export_history()`: include `"rule_variant": self.variant`.

## Global Constraints
- Zero Node.js / npm runtime dependencies. Pure Python 3.10+.
- Backward compatibility: Any call without `variant` argument behaves exactly as before (`standard`).
- All code comments and docstrings in clear English.
- No decorative emojis in code, comments, or commit messages.
- Must pass `pytest tests/test_game_variants.py tests/test_engine.py -v`.
- Commit message: `feat(engine): add rule variant support with inverted combat cycle`.
