# Merge All Feature Branches into Main Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fully automate the merge and integration of branches `feature/live-tournament-projections`, `feature/ui`, `fix/bracket-playoff-flow`, and `feature/wan-deployment` into `main` with zero regressions and all tests passing.

**Architecture:** Create an isolated git worktree for integration. Merge `feature/live-tournament-projections` and `feature/ui` (noting that `fix/bracket-playoff-flow` and `feature/wan-deployment` are already merged on `main`). Systematically resolve all 15 file conflicts by uniting live multi-board bracket projections, custom rule engines, multi-game support (caro, connect4), clubhouse/arena UI, and admin controls. Run full pytest verification and update Single Source of Truth (`docs/CONTEXT_RESUME.md`, `TASKS.md`).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy, SQLite, Jinja2, HTML5/CSS3/Vanilla JS (Zero-Node.js), Pytest.

**Spec:** Merge integration of live multi-board bracket tournament projections, custom movement/tiebreak rules, and multi-game arena UI into main branch.

## Global Constraints
- Pure HTML5/CSS3/Vanilla JS served by FastAPI — Never introduce npm/Node.js dependencies.
- Code comments, docstrings, commit messages strictly in English.
- Single Source of Truth architecture: update `docs/CONTEXT_RESUME.md` and `TASKS.md` with every architectural modification.
- All existing and new tests must pass (`pytest -v`).
- Root reference preservation: `resources/` and root meta-files (`.gemini/`, `GEMINI.md`, `CLAUDE.md`, `docs/CONTEXT_RESUME.md`) must strictly stay at the repository root and never be duplicated into worktrees.

## Review Focus
1. `engine/runner.py`: Ensure `run_match` correctly supports both `variant` (standard, inverted_rps, custom) with tiebreak scores/goals, `progress_callback`, and `game_type` (rps9x9 vs grid games like connect4, caro).
2. `server/database.py` & `server/models.py`: Retain both `live_moves` in Match and `game_type` in Bot and Match schemas.
3. `server/routes/admin.py`: Support both live tournament lifecycle controls (speed up, end tournament, custom rules) and game catalog / game type switching.
4. `server/routes/matches.py`: Support both `live_moves` fallback streaming when replay is generating, and `game_type` active bot validation.
5. `web/templates` and `web/static`: Ensure bracket view displays live multi-board canvas projections within the new UI layout without broken markup or JavaScript errors.

---

### Task 1: Setup Isolated Git Worktree
- [ ] Announce using `using-git-worktrees` skill.
- [ ] Create isolated integration branch `merge/all-branches` from `main`.
- [ ] Create worktree at `.worktrees/merge-branches` checking out `merge/all-branches`.
- [ ] Verify directory isolation and root reference preservation.

### Task 2: Merge `feature/live-tournament-projections`
- [ ] Merge `origin/feature/live-tournament-projections` into `merge/all-branches` inside worktree.
- [ ] Verify clean automatic merge.
- [ ] Run pytest to verify all existing and new projection tests pass.

### Task 3: Merge `feature/ui` & Resolve All 15 Conflicts
- [ ] Initiate merge of `origin/feature/ui` into `merge/all-branches`.
- [ ] Resolve conflicts in documentation & tasks:
  - [ ] `TASKS.md`
  - [ ] `docs/ADMIN_GUIDE.md`
  - [ ] `docs/CONTEXT_RESUME.md`
- [ ] Resolve conflicts in core engine & models:
  - [ ] `engine/runner.py` (combine live progress callbacks, custom rule variants, tiebreak goals with multi-game grid support)
  - [ ] `server/models.py` (retain both `live_moves` and `game_type`)
  - [ ] `server/database.py` (retain both tournament settings, custom rule serialization, speedup/live updates)
  - [ ] `server/queue.py` (ensure match runner passes live callback and respects game_type)
- [ ] Resolve conflicts in routes & CLI:
  - [ ] `server/routes/admin.py` (merge custom rules, speedup, end-tournament with catalog management)
  - [ ] `server/routes/matches.py` (merge live moves streaming replay endpoint with multi-game bot validation)
  - [ ] `starter_kit/local_arena.py` (merge custom rule arguments with multi-game local arena options)
- [ ] Resolve conflicts in frontend assets & templates:
  - [ ] `web/static/css/style.css` (integrate bracket live board styles into the redesigned stylesheet)
  - [ ] `web/static/js/visualizer.js` (merge live board updates with UI visualizer improvements)
  - [ ] `web/templates/admin.html` (combine live tournament controls with game catalog)
  - [ ] `web/templates/bracket.html` (combine live multi-board projections with redesigned bracket UI)
  - [ ] `web/templates/replay.html` (combine live match view indicator with redesigned replay UI)
- [ ] Complete git merge commit.

### Task 4: Comprehensive Test Verification & TDD
- [ ] Run full test suite with `pytest -v`.
- [ ] Fix any failing tests or regressions.
- [ ] Add integration test verifying both live tournament projections and multi-game routes coexist cleanly.
- [ ] Confirm 100% green tests.

### Task 5: Fast-forward / Integrate into `main` & Clean Up Worktree
- [ ] Fast-forward or merge `merge/all-branches` into `main`.
- [ ] Run `pytest -v` on `main` to confirm total test success.
- [ ] Remove git worktree `.worktrees/merge-branches` and delete temporary branch.
- [ ] Update `TASKS.md` and `docs/CONTEXT_RESUME.md` to reflect full integration.
