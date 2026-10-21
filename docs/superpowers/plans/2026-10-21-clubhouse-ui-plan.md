# Unified Clubhouse 2.0, Vietnamese Typography & Student Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Standardize the web interface into Unified Clubhouse 2.0, fix all Vietnamese font rendering issues using `Be Vietnam Pro`, eliminate stylesheet conflicts, and rewrite the student guide to be warm, human, and pedagogical.

**Architecture:** Load `Be Vietnam Pro` (display & body) and `JetBrains Mono` (code/numbers) via CDN in `base.html`, update root font variables in `style.css` and `clubhouse.css`, harmonize design tokens across all views (`bracket`, `replay`, `admin`, `grade`), and revamp `guide.html` into a friendly student onboarding experience.

**Tech Stack:** FastAPI, Jinja2, HTML5, CSS3 (Neo-Brutalism tokens), Vanilla JS, Pytest.

**Spec:** `docs/superpowers/specs/2026-10-21-clubhouse-ui-vietnamese-font-design.md`

## Global Constraints
- Zero-Node.js: Pure HTML5/CSS3/Vanilla JS served by FastAPI. Never introduce npm/node runtime dependencies.
- Code Comments: All code comments, docstrings, and commit messages MUST be in clear, detailed English.
- Single Source of Truth: Update `docs/CONTEXT_RESUME.md` and `TASKS.md` immediately with any architectural or visual changes.
- Isolated Worktree: Develop on branch `feature/ui-clubhouse-polish` in `.worktrees/ui-clubhouse-polish`.
- Testing: Run full test suite with `pytest -v` to ensure 100% pass rate before merging.

## Review Focus
- Input: Vietnamese text containing composite diacritics (e.g. `ở`, `ẵ`, `ệ`, `đ`, `Bảng xếp hạng`). Expected: Renders cleanly with `Be Vietnam Pro` without font fallback jumping.
- Input: Mobile viewport at 375px width. Expected: No horizontal scroll bar caused by rotated stickers (`transform: rotate(...)`).
- Input: Tournament Bracket view (`/bracket`) and Replay view (`/replay/<id>`). Expected: Clean Clubhouse card aesthetic with ink border and warm background, no broken dark-mode leftovers.
- Input: Guide page (`/guide`). Expected: Student-friendly tone, explaining `get_move(board, my_player, history)` with concrete examples.
- Input: Full regression test suite. Expected: All existing 416+ tests pass without errors.

---

### Task 1: Web Fonts & Base Typography Setup

**Files:**
- Create: `tests/test_ui_typography.py`
- Modify: `web/templates/base.html`
- Modify: `web/static/css/style.css:34-37`
- Modify: `web/static/css/clubhouse.css:13-14`

- [ ] Step 1: Write failing test in `tests/test_ui_typography.py` checking that `/` and `/guide` templates load `Be+Vietnam+Pro` Google Font and contain no `Bahnschrift` or `Trebuchet MS` in primary font-family tokens.
- [ ] Step 2: Run `pytest tests/test_ui_typography.py -v` and verify failure.
- [ ] Step 3: In `web/templates/base.html`, add Google Font preconnect and stylesheet link for `Be Vietnam Pro` (weights 400, 500, 600, 700, 800) and `JetBrains Mono` (weights 400, 500, 700).
- [ ] Step 4: In `web/static/css/style.css`, update `--font-sans`, `--font-display`, and `--font-mono` to prioritize `Be Vietnam Pro` and `JetBrains Mono`.
- [ ] Step 5: In `web/static/css/clubhouse.css`, update `--font-sans` and `--font-display` to `"Be Vietnam Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`.
- [ ] Step 6: Re-run `pytest tests/test_ui_typography.py -v` and confirm green pass.
- [ ] Step 7: Commit changes with message `feat(ui): add Be Vietnam Pro and JetBrains Mono typography stack`.

---

### Task 2: Design Token Harmonization & CSS Polish across Pages

**Files:**
- Create: `tests/test_ui_pages_consistency.py`
- Modify: `web/static/css/clubhouse.css`
- Modify: `web/static/css/site.css`
- Modify: `web/templates/bracket.html`
- Modify: `web/templates/replay.html`
- Modify: `web/templates/admin.html`

- [ ] Step 1: Write integration tests in `tests/test_ui_pages_consistency.py` checking that `/bracket`, `/admin`, and replay templates render with 200 OK and inherit base styling.
- [ ] Step 2: In `web/static/css/clubhouse.css`, unify card borders, remove hardcoded dark clashes, and refine mobile responsive rules:
  - Disable heavy rotations on mobile (`@media (max-width: 640px) { .brand-badge, .club-mascot, .club-sticker { transform: none !important; } }`).
  - Add Clubhouse styling rules for bracket cards (`.bracket-match`, `.round-col`, `.bracket-title`) and replay panel (`.board-container`, `.replay-card`).
  - Ensure interactive buttons meet min-height 42-44px for touch accessibility.
- [ ] Step 3: Run `pytest tests/test_ui_pages_consistency.py -v` and confirm pass.
- [ ] Step 4: Commit changes with message `feat(ui): harmonize Clubhouse design tokens across bracket, replay, and admin views`.

---

### Task 3: Student-Friendly Human-Centric Guide Overhaul (`guide.html`)

**Files:**
- Modify: `web/templates/guide.html`
- Modify: `tests/test_ui_typography.py`

- [ ] Step 1: Add assertions to `tests/test_ui_typography.py` to check for key student-friendly guide sections: "Quy tắc 60 giây", "Cấu trúc hàm get_move", "Chiến lược cho người mới", "Kiểm tra với local_arena".
- [ ] Step 2: Rewrite `web/templates/guide.html` with an engaging, empathetic tone:
  - Phase 1: Chào đón & Tóm tắt nhanh quy tắc cờ Oẳn Tù Tì 9×9 (Kéo - Bao - Búa, ăn quân, góc đích).
  - Phase 2: Khám phá `bot_template.py` và giải mã hàm `get_move(board, my_player, history)`.
  - Phase 3: Minh họa cấu trúc dữ liệu `board` (9 hàng, 9 cột) và danh sách nước đi hợp lệ.
  - Phase 4: Hướng dẫn 3 cấp độ chiến thuật (Từ Random đơn giản -> Săn mồi gần -> Tiến về góc đích).
  - Phase 5: Hướng dẫn chạy `python local_arena.py` để đấu thử ngay trên máy không cần mạng.
  - Phase 6: Các lỗi thường gặp (Timeout 1.0s, Nước đi ngoài bàn cờ, Import bị cấm) và cách khắc phục.
- [ ] Step 3: Run `pytest tests/test_ui_typography.py -v` and confirm all assertions pass.
- [ ] Step 4: Commit changes with message `docs(guide): rewrite guide.html with friendly student-centric mentorship walkthrough`.

---

### Task 4: SSOT Documentation Update & Full Test Verification

**Files:**
- Modify: `docs/CONTEXT_RESUME.md`
- Modify: `TASKS.md`

- [ ] Step 1: Update `docs/CONTEXT_RESUME.md` with Section 28 (Unified Clubhouse 2.0 & Vietnamese Typography System).
- [ ] Step 2: Update `TASKS.md` with Task 13 (Clubhouse UI 2.0 & Student Guide Revamp).
- [ ] Step 3: Run full test suite `pytest -v` and confirm 100% pass rate.
- [ ] Step 4: Commit changes with message `docs: update SSOT docs for Unified Clubhouse 2.0 and student guide`.
