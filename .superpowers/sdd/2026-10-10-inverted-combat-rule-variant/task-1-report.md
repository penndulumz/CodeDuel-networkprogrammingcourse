# Task 1 Implementation Report: Engine Layer Rule Variant Support

## Overview
Implemented rule variant architecture in `engine/game.py` supporting both standard RPS rules and the Inverted Combat Cycle (`inverted_rps`: Scissors beats Rock, Rock beats Paper, Paper beats Scissors). All changes preserve strict backward compatibility where omitting the variant argument defaults to `standard`.

## Changes Implemented

### 1. `engine/game.py`
- **Rule Variant Constants**:
  - `RULE_VARIANT_STANDARD = "standard"`
  - `RULE_VARIANT_INVERTED_RPS = "inverted_rps"`
  - `SUPPORTED_RULE_VARIANTS = ["standard", "inverted_rps"]`
- **Combat Logic (`beats`)**:
  - Updated signature: `beats(a: str, b: str, variant: str = RULE_VARIANT_STANDARD) -> bool`.
  - Inverted rules: Scissors beats Rock, Rock beats Paper, Paper beats Scissors.
  - Standard rules: Rock beats Scissors, Scissors beats Paper, Paper beats Rock.
  - Fallback: Any unknown or unrecognized variant defaults to standard rules.
- **Move Validation & Execution**:
  - `_parse_move_positions`: Robust parsing of coordinate tuples `((fr, fc), (tr, tc))` and dictionary formats `{"from": ..., "to": ...}`.
  - `is_valid_move(board, move, player, variant: str = RULE_VARIANT_STANDARD) -> bool`: Enforces board boundaries, movement distance, piece ownership, and variant combat rules.
  - `make_move(board, move, player, variant: str = RULE_VARIANT_STANDARD) -> tuple[board, move_dict]`: Applies legal moves on an isolated board copy, generating standard SAN notation.
  - `generate_legal_moves(board, player, variant: str = RULE_VARIANT_STANDARD)`: Enumerates all valid candidate moves for a player under the active variant.
- **Game / GameState Class**:
  - Updated `__init__` with `variant: str = RULE_VARIANT_STANDARD`, setting `self.variant` and `self.rule_variant`.
  - Updated internal methods (`get_valid_destinations`, `get_valid_moves`, `apply_move`) to pass `self.variant` to `beats`.
  - Added convenience methods `is_valid_move`, `make_move`, and `generate_legal_moves`.
  - Updated `clone()` to preserve `variant`.
  - Updated `to_dict()` and added `export_history()` to serialize `rule_variant` alongside match history.
  - Maintained bidirectional alias: `GameState = Game`.

### 2. `tests/test_game_variants.py`
Created comprehensive unit tests covering:
- Variant constant exposures (`test_constants_defined`).
- Strict comparison outcomes across all permutations under standard vs inverted cycles (`test_beats_standard_vs_inverted`).
- Movement validity combat checks under inverted vs standard (`test_is_valid_move_combat_inverted`, `test_is_valid_move_non_combat_and_invalid_formats`).
- Move execution, capture resolution, and non-mutation (`test_make_move_combat_resolution_inverted`).
- Legal move generation filtering based on variant (`test_generate_legal_moves_respects_variant`).
- Game instance lifecycle, cloning isolation, and serialization (`test_game_class_variant_lifecycle`, `test_game_instance_moves_and_combat_inverted`).
- Full wipeout victory condition under inverted combat (`test_full_wipeout_under_inverted_rules`).

## TDD Verification
1. **Red Phase**: Executed `pytest tests/test_game_variants.py -v`. Confirmed failure on `ImportError: cannot import name 'Game' from 'engine.game'`.
2. **Green Phase**: Implemented changes in `engine/game.py`.
3. **Verification**: Executed `pytest tests/test_game_variants.py tests/test_engine.py -v`:
   - 26 tests collected, 26 passed (0.07s).
4. **Full Suite Regression**: Executed `pytest -v` across entire repository:
   - 342 tests collected, 342 passed (14.54s).

## Git Commit
- **Commit Hash**: `fdf8d74`
- **Commit Title**: `feat(engine): add rule variant support with inverted combat cycle`
- **Staged Files**: `engine/game.py`, `tests/test_game_variants.py`
