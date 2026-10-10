# Task 3 Brief: Admin Web Management & Tournament API Integration

## Objective
Enable tournament administrators to configure and toggle the active tournament rule variant (`rule_variant`, e.g. `standard` or `inverted_rps`) directly via the Admin portal and REST API, and ensure match challenge creation inherits this active setting.

## Target Files
1. `tests/test_admin_schedule.py`:
   - Add unit/integration tests verifying:
     - `GET /api/admin/settings` returns `rule_variant` field.
     - `POST /api/admin/settings` persists `rule_variant="inverted_rps"` and updates database.
     - `POST /api/admin/settings` with invalid `rule_variant` (e.g. `"unsupported"`) returns HTTP 400 Bad Request.
2. `server/routes/admin.py`:
   - In `UpdateSettingsRequest`: Add `rule_variant: Optional[str] = None`.
   - In `_get_all_settings_dict`: Include `"rule_variant": settings_map.get("rule_variant", "standard")`.
   - In `update_settings`:
     - If `payload.rule_variant is not None`:
       - Validate that `payload.rule_variant.strip()` is in `["standard", "inverted_rps"]` (or `engine.game.SUPPORTED_RULE_VARIANTS`).
       - If invalid, raise `HTTPException(status_code=400, detail="Unsupported rule variant.")`.
       - `_upsert_setting(db, "rule_variant", payload.rule_variant.strip())`.
3. `server/routes/matches.py`:
   - In `create_challenge`: When instantiating `Match(...)`, copy active variant:
     ```python
     setting = db.query(TournamentSetting).filter(TournamentSetting.key == "rule_variant").first()
     active_variant = setting.value if setting and setting.value else "standard"
     ```
     and pass `rule_variant=active_variant`.
4. `web/templates/admin.html`:
   - Add `<div class="form-group">` with `<select id="rule_variant" name="rule_variant">` offering:
     - `standard`: "Tiêu chuẩn (Standard: Búa > Kéo > Bao)"
     - `inverted_rps`: "Đảo chiều ngũ hành (Inverted Combat: Kéo > Búa > Bao)"
   - In JavaScript `handleSettingsSubmit`: send `rule_variant: document.getElementById('rule_variant').value` in payload.

## Global Constraints
- Zero Node.js / npm dependencies. Pure Python 3.10+, FastAPI, Jinja2, Vanilla JS.
- Slate/Charcoal palette styling consistent with existing form controls.
- All code comments and docstrings in clear English.
- No decorative emojis in code, comments, or commit messages.
- Must pass `pytest tests/test_admin_schedule.py tests/test_admin_security.py -v`.
- Commit message: `feat(admin): add dynamic rule variant configuration to admin portal`.
