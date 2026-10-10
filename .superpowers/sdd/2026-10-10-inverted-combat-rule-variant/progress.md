# SDD ledger — plan: docs/superpowers/plans/2026-10-10-inverted-combat-rule-variant.md

## Preflight Plan Scan
| Tasks | Shared Interface / File | Status | Notes |
|:---|:---|:---|:---|
| Task 1 -> Task 2 | `Game(variant=...)` in `engine/runner.py` and `server/queue.py` | Clean | Parameters and defaults align |
| Task 2 -> Task 3 | `TournamentSetting.rule_variant` updated in admin routes | Clean | Enum/string values match |
| Task 1 & 2 -> Task 4 | `local_arena.py` `--variant` and replay badge | Clean | Value `inverted_rps` matches |
| Task 1-4 -> Task 5 | Docs synchronization for new variant architecture | Clean | Covers SSOT updates |

## Progress
- [x] Task 1: Engine Layer Rule Variant Support
- [x] Task 2: Database Schema & Background Queue Variant Execution
- [x] Task 3: Admin Web Management & Tournament API Integration
- [x] Task 4: Starter Kit Local Arena & Replay Visualizer Integration
- [x] Task 5: Documentation Harmonization & Continuous Feedback Loop

Task 1: complete (commits e542d0d..fdf8d74, review clean)
Task 2: complete (commits f54edd3..db23d4f, review clean)
Task 3: complete (commits ff57a32..33d4a8b, review clean)
Task 4: complete (commits c47c3a0..7d9d694, review clean)
Task 5: complete (commits b63677e..800cead, review clean)
