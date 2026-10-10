# Inverted Combat Rule Variant Architecture Specification

## 1. Overview & Objective
To verify that tournament participants genuinely understand their bot implementations and can adapt under constrained offline conditions (Day N+1 offline defense session), the Battlecode RPS 9x9 Platform introduces dynamic Rule Variant support. The primary variant implemented is **Inverted Combat Cycle** (`inverted_rps`), reversing the traditional Rock-Paper-Scissors hierarchy:
- Traditional: Rock beats Scissors, Scissors beats Paper, Paper beats Rock ($R > S > P > R$).
- Inverted: Scissors beats Rock, Rock beats Paper, Paper beats Scissors ($S > R > P > S$).

Participants receive 2 hours offline to inspect the rule update, adjust their bot's internal combat logic, test locally via `starter_kit/local_arena.py --variant inverted_rps`, and submit their revised bot.

---

## 2. Global Constraints & Architectural Invariants
- **Zero-Node.js & Pure Python/FastAPI/SQLite WAL**: No runtime npm dependencies.
- **Backward Compatibility**: Standard mode (`standard`) remains default everywhere; existing matches, tests, and replays retain standard mechanics.
- **Zero-Emoji Documentation Invariant**: All documentation, code comments, and commit messages must strictly avoid decorative emojis.
- **Continuous Feedback Loop Law**: Schema additions and engine parameters must be synchronized with `docs/CONTEXT_RESUME.md` and `TASKS.md`.
- **Test-Driven Development (TDD)**: All functionality covered by rigorous unit and integration tests.

---

## 3. Detailed Component Architecture

### 3.1 Engine Layer (`engine/game.py`)
1. **Constants**:
   ```python
   RULE_VARIANT_STANDARD: str = "standard"
   RULE_VARIANT_INVERTED_RPS: str = "inverted_rps"
   SUPPORTED_RULE_VARIANTS: list[str] = [RULE_VARIANT_STANDARD, RULE_VARIANT_INVERTED_RPS]
   ```
2. **`beats(a: str, b: str, variant: str = RULE_VARIANT_STANDARD) -> bool`**:
   - If `variant == RULE_VARIANT_INVERTED_RPS`:
     `(a == "S" and b == "R") or (a == "R" and b == "P") or (a == "P" and b == "S")`
   - Else:
     `(a == "R" and b == "S") or (a == "S" and b == "P") or (a == "P" and b == "R")`
3. **`Game` Class**:
   - `__init__(self, variant: str = RULE_VARIANT_STANDARD)`: Stores `self.variant`.
   - `is_valid_move`, `make_move`, `generate_legal_moves`: Pass `self.variant` to `beats`.
   - `clone()`: Preserves `variant`.
   - `to_dict()` / history serialization: Includes `rule_variant` field in match metadata.

### 3.2 Subprocess Runner & Background Queue (`engine/runner.py`, `server/queue.py`)
- `GameRunner.play_match`: Accepts `variant: str = RULE_VARIANT_STANDARD` and initializes `Game(variant=variant)`.
- `server/queue.py`:
  - When dequeuing a match, fetches active `rule_variant` from `TournamentSetting` (or `match.rule_variant` if specified on match record).
  - Passes `variant` to `runner.play_match`.
  - Persists `rule_variant` on the `Match` record upon completion.

### 3.3 Database Models & Migration (`server/models.py`)
- `Match`: Add column `rule_variant = Column(String(32), default="standard", nullable=False)`.
- `TournamentSetting`: Add column `rule_variant = Column(String(32), default="standard", nullable=False)`.

### 3.4 Admin Portal & Web API (`server/routes/admin.py`, `web/templates/admin.html`)
- `TournamentSettingUpdate` schema: Add `rule_variant: Optional[str] = "standard"`.
- Admin UI (`web/templates/admin.html`):
  - Dynamic dropdown selector for Tournament Rule Variant:
    - `standard`: "Tiêu chuẩn (Búa > Kéo > Bao)"
    - `inverted_rps`: "Đảo chiều ngũ hành (Kéo > Búa > Bao)"
  - Updates persist into `TournamentSetting` immediately.

### 3.5 Offline Starter Kit (`starter_kit/local_arena.py`)
- CLI argument `--variant` (choices: `standard`, `inverted_rps`, default: `standard`).
- Simulates matches locally under the selected variant, printing combat results and victory reasons.

### 3.6 Replay Visualizer (`web/templates/replay.html`, `web/static/js/visualizer.js`)
- Replay header displays a status badge when `rule_variant == "inverted_rps"`:
  `Chế độ: Đảo chiều ngũ hành (Kéo > Búa > Bao)`.

---

## 4. Testing & Verification Matrix
1. `tests/test_game_variants.py`:
   - Unit tests for `beats()` under standard vs inverted modes.
   - Legal move generation and combat resolution under inverted rules.
   - Full simulated game victory under inverted rules.
2. `tests/test_admin_schedule.py` & `tests/test_admin_security.py`:
   - Admin API persistence and validation for `rule_variant`.
3. `tests/test_queue.py`:
   - Background match processing preserving `rule_variant` in database.
4. `tests/test_starter_kit.py`:
   - `local_arena.py --variant inverted_rps` CLI execution.
5. `tests/test_documentation_integrity.py`:
   - Verify Section 17 in `docs/CONTEXT_RESUME.md`, Milestone 11 in `TASKS.md`, zero emojis.
