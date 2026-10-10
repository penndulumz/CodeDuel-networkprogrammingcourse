# Task 5 Brief: Documentation Harmonization & Continuous Feedback Loop

## Objective
Harmonize documentation across `docs/CONTEXT_RESUME.md`, `TASKS.md`, `README.md`, and `tests/test_documentation_integrity.py`.
Adhere strictly to the Continuous Feedback Loop Law, Single Source of Truth (SSOT), and Zero-Emoji Invariant.

## Target Files
1. `tests/test_documentation_integrity.py`:
   - Add `test_context_resume_rule_variant_content()` asserting that Section 17 in `docs/CONTEXT_RESUME.md` covers `inverted_rps`, `rule_variant`, and `Inverted Combat`.
   - Add `test_tasks_milestone_11_content()` asserting that `Milestone 11` and subtasks `11.1` through `11.5` are documented in `TASKS.md`.
2. `docs/CONTEXT_RESUME.md`:
   - Add Section 17: "Hệ Thống Biến Thể Luật Chơi & Đấu Trường Đảo Chiều Ngũ Hành (Tournament Rule Variants & Inverted Combat Cycle)".
   - Detail the Inverted Combat mechanics ($S > R > P > S$), engine parameters (`variant`), persistence in `Match.rule_variant` and `TournamentSetting(key="rule_variant")`.
   - Detail Admin configuration via `/api/admin/settings` and CLI offline testing via `starter_kit/local_arena.py --variant inverted_rps`.
   - Maintain 100% emoji-free academic tone.
3. `TASKS.md`:
   - Add Milestone 11: "Hệ Thống Biến Thể Luật Chơi Động & Đảo Chiều Ngũ Hành (Inverted Combat Rule Variant) (Cả Nhóm)".
   - Detail Tasks 11.1 through 11.5 with verification metrics and links to spec and plan.
   - Maintain 100% emoji-free tone.
4. `README.md`:
   - Update Section 1 / Section 3 mentioning offline testing with `--variant inverted_rps` and dynamic rule variant support.

## Global Constraints
- Zero decorative emojis in any markdown documentation file.
- All code comments and docstrings in clear English.
- Verify with `pytest tests/test_documentation_integrity.py -v`.
- Full regression verification: `pytest -q` passing 100%.
- Commit message: `docs: synchronize inverted combat rule variant architecture and milestone records`.
