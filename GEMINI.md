# GEMINI.md — Persistent Context & Instructions for Gemini & Antigravity

> **Notice for Gemini / Antigravity Agents**:
> This file is automatically loaded into your context. You are working on the **Battlecode RPS Platform** (9x9 Rock-Paper-Scissors Chess tournament system).
> Follow the principles and conventions defined below across all sessions without requiring the user to re-paste master prompts.

---

## 1. Project Overview & Architecture
- **Purpose**: Battlecode-style tournament platform for 9×9 Rock-Paper-Scissors chess. Students submit Python bots to compete 1v1.
- **Tech Stack**:
  - **Backend**: Python 3.10+, FastAPI, SQLAlchemy (SQLite with WAL mode).
  - **Frontend**: Pure HTML5, CSS3, Vanilla JavaScript (Jinja2 templates, zero Node.js/npm runtime dependencies).
  - **Engine**: Pure Python 9x9 game engine (`engine/game.py`), AST security sandbox (`engine/sandbox.py`), isolated subprocess runner (`engine/runner.py`).
  - **Tournament**: Daily FFA window with randomized Elo multiplier $x$, Final-day single-elimination Bracket tournament (BO3), normalized scoring formula.

---

## 2. Global Constraints & Standards
1. **Zero-npm**: Never introduce Node.js or npm build steps. The frontend is vanilla HTML/CSS/JS served directly via FastAPI.
2. **Code Comments**: All code comments, docstrings, and commit messages MUST be written in **clear, detailed English**.
3. **Board Rules & Coordinates**:
   - 9×9 grid: `row: 0..8`, `col: 0..8`. Row 0 = Rank 1, Row 8 = Rank 9. Col 0 = File a, Col 8 = File i.
   - Pieces: `'R'` (Rock), `'P'` (Paper), `'S'` (Scissors). Hierarchy: `R > S`, `S > P`, `P > R`.
   - Player 1 (Red) starts row 0, goal is `i9` (`row=8, col=8`).
   - Player 2 (Blue) starts row 8, goal is `a1` (`row=0, col=0`).
   - Win conditions: Goal reach, 3-piece wipeout of any type, forfeit (timeout 1.0s or crash), or turn 200 tiebreaker (piece count).
4. **Bot API Signature**:
   ```python
   def get_move(board: list[list[dict | None]], my_player: int, history: list[dict]) -> tuple[tuple[int, int], tuple[int, int]]:
   ```
5. **Testing**: Always run `pytest` to verify before committing. All tests live in `tests/`.

---

## 3. Team Member Division (4 Roles)
- **Member 1 (Engine Lead)**: `engine/game.py`, `engine/sandbox.py`, `starter_kit/`, `tests/test_game.py`, `tests/test_sandbox.py`.
- **Member 2 (Execution Lead)**: `engine/runner.py`, `server/queue.py`, `tests/test_runner.py`.
- **Member 3 (Backend & Tournament Lead)**: `server/models.py`, `server/database.py`, `server/tournament.py`, `config/tournament.yaml`, `tests/test_database.py`, `tests/test_tournament.py`.
- **Member 4 (Frontend & Visualizer Lead)**: `web/templates/`, `web/static/`, `server/main.py`, `tests/test_web.py`.

---

## 4. Superpowers Skill Lifecycle Integration
When receiving any feature request or bug report:
1. **Brainstorming & Design**: Use `brainstorming` before making changes.
2. **Planning**: Use `writing-plans` to produce bite-sized TDD tasks.
3. **Execution**: Use `subagent-driven-development` or `test-driven-development` to ensure failing tests precede implementation.
4. **Debugging**: Use `systematic-debugging` if encountering any failures.
5. **Verification**: Always run `pytest` to guarantee all tests pass.
6. **Finishing**: Use `finishing-a-development-branch` to integrate cleanly into `main`.
