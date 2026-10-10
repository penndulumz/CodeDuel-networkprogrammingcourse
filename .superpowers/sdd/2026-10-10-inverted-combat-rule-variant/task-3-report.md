# Task 3 Implementation Report: Admin Web Management & Tournament API Integration

## Executive Summary
Task 3 implemented dynamic rule variant administration via the Admin portal and REST API, enabling tournament administrators to toggle the active tournament combat rules (`standard` vs `inverted_rps`), validating input against supported engine variants, persisting settings to SQLite, and automatically propagating the active rule variant to newly created match challenges.

## Changes Implemented
1. **Admin REST API (`server/routes/admin.py`)**:
   - Updated `UpdateSettingsRequest` schema with `rule_variant: Optional[str] = None`.
   - Updated `_get_all_settings_dict` to read `rule_variant` from `TournamentSetting` with fallback to `"standard"`.
   - Updated `update_settings` endpoint to validate candidate variants against `engine.game.SUPPORTED_RULE_VARIANTS` and reject invalid variants with `HTTPException(status_code=400, detail="Unsupported rule variant.")`.
   - Persisted valid variants via `_upsert_setting(db, "rule_variant", candidate_variant)`.

2. **Match Challenge Integration (`server/routes/matches.py`)**:
   - In `challenge_opponent`, queried active `rule_variant` from `TournamentSetting` (defaulting to `"standard"`).
   - Instantiated new `Match` entities with `rule_variant=active_variant`.
   - Included `"rule_variant": getattr(m, "rule_variant", "standard")` in `_serialize_match`.

3. **Admin Web Template (`web/templates/admin.html`)**:
   - Added `rule_variant` form control group with `<select id="rule_variant" name="rule_variant">` supporting:
     - `standard`: Tiêu chuẩn (Standard: Búa > Kéo > Bao)
     - `inverted_rps`: Đảo chiều ngũ hành (Inverted Combat: Kéo > Búa > Bao)
   - Updated `handleUpdateSettings` JavaScript payload to serialize and submit the selected `rule_variant`.

4. **Integration & Regression Tests (`tests/test_admin_schedule.py`)**:
   - `test_admin_settings_rule_variant_get_and_update`: Confirmed default `"standard"` retrieval, update to `"inverted_rps"`, persistence in `TournamentSetting`, and subsequent GET query reflecting the new setting.
   - `test_admin_settings_rule_variant_invalid_rejected`: Confirmed rejection with HTTP 400 for unsupported variant values.
   - `test_challenge_opponent_inherits_active_rule_variant`: Confirmed `/api/matches/challenge` sets `match.rule_variant == "inverted_rps"` according to active tournament settings, and serialized match details reflect the variant.

## Test Verification
- `pytest tests/test_admin_schedule.py -k "rule_variant" -v`: Initial run demonstrated expected failure; post-implementation demonstrated 3 passing tests.
- `pytest tests/test_admin_schedule.py tests/test_admin_security.py -v`: All 13 tests passed.
- `pytest -v`: Full test suite passed with 349 passing tests and 0 regressions.

## Git Commit
- Hash: `33d4a8b`
- Message: `feat(admin): add dynamic rule variant configuration to admin portal`
