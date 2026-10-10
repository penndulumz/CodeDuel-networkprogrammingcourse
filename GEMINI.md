# GEMINI.md — Persistent Pointer & Instructions for Gemini & Antigravity

> **Notice for Gemini & Antigravity Agents**:
> This project operates under a strict **Single Source of Truth (SSOT)** architecture.
> **DO NOT define new rules, divergent workflows, or duplicate architectures in this file.**
> Doing so causes divergence when other teammates use `CLAUDE.md`, `.cursorrules`, or alternate LLMs.

---

## 1. Single Source of Truth References
Before executing any action, answering questions, or proposing changes, you MUST read and ground your decisions in the existing central project files:
1. 📄 **[`docs/CONTEXT_RESUME.md`](docs/CONTEXT_RESUME.md)**: **The supreme authoritative source** for:
   - System architecture & database schemas.
   - Core game rules (9x9 board, Rock-Paper-Scissors hierarchy, goal reaching, wipeouts).
   - Bot API signature (`get_move(board, my_player, history)`).
   - 4-member roles & team division.
   - **Continuous Feedback Loop Law**: If you make any breaking change or architectural alteration, you **MUST** update `docs/CONTEXT_RESUME.md` immediately in that same change.
2. 📖 **[`README.md`](README.md)**: Entry point for user guides, setup instructions, folder structure, and CLI usage.
3. 📋 **[`TASKS.md`](TASKS.md)**: Active task tracking, milestones, and verification acceptance criteria.

---

## 2. Global Constraints Summary
- **Zero-Node.js**: Pure HTML5/CSS3/Vanilla JS served by FastAPI. Never introduce npm/node runtime dependencies.
- **Code Comments**: All code comments, docstrings, and commit messages MUST be in clear, detailed English.
- **Testing Before Completion**: Run `pytest -v` to verify any modifications before committing.
- **Worktree Isolation**: Always develop new features in an isolated worktree (`.worktrees/<branch-name>`).
- **Root Reference Preservation**: `resources/` and root meta-files (`.gemini/`, `GEMINI.md`, `CLAUDE.md`, `docs/CONTEXT_RESUME.md`) must strictly stay at the repository root and NEVER be duplicated into worktrees.
- **Single-Admin & LAN Access**: Only 1 admin account exists (configurable via `ADMIN_USERNAME`/`ADMIN_PASSWORD` env vars); server listens on `0.0.0.0:8000` with LAN URL auto-detection.

---

## 3. Engineering Development Lifecycle
When implementing features, fixes, or maintenance:
1. **Explore & Design**: Clarify requirements and architectural specifications before making changes.
2. **Plan**: Generate bite-sized TDD implementation tasks with clear verification criteria.
3. **Execute**: Implement via Test-Driven Development (TDD).
4. **Debug**: Systematically isolate root cause before modifying code.
5. **Verify**: Run full test verification with `pytest -v`.
6. **Finish**: Cleanly integrate verified changes into `main`.
