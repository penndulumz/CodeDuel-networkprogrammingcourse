# Ke Hoach Thuc Hien & Theo Doi Tien Do Du An (TASKS.md)

> **Trang thai**: Hoan thanh toan dien va toan bo test pass (240/240 tests pass).
> - Quy tac: Da kiem chung tu dong toan dien qua Subagent-Driven Development, 6-domain Deep Testing Matrix, va Unit/Integration/E2E test suite.

---

## Milestone 0: Khoi Tao Du An & Moi Truong Chung (Ca Nhom)
- [x] **Task 0.1**: Tao file `requirements.txt` voi cac thu vien cot loi (`fastapi`, `uvicorn`, `sqlalchemy`, `pyyaml`, `jinja2`, `python-multipart`, `pytest`).
  - *Verification*: Da cai dat va kiem tra tren Python 3.13 / 3.10+.
- [x] **Task 0.2**: Tao file cau hinh mau `config/tournament.yaml`.
  - *Verification*: Doc duoc file bang PyYAML khong bi loi cu phap (`load_tournament_config`).

---

## Milestone 1: Core Engine & Bot Starter Kit (Phu trach: Member 1)
- [x] **Task 1.1**: Viet Game Logic 9x9 trong `engine/game.py` (Ban co, quan R/P/S, luat an quan, kiem tra cham dich i9/a1, kiem tra diet sach quan).
  - *Verification*: Chay `pytest tests/test_game.py` -> 17/17 tests PASS.
- [x] **Task 1.2**: Viet bo loc bao mat AST trong `engine/sandbox.py` (Phat hien va cam import `os`, `sys`, `socket`, `open`, `eval`...).
  - *Verification*: Chay `pytest tests/test_sandbox.py` -> 74/74 tests PASS.
- [x] **Task 1.3**: Xay dung goi `starter_kit/` (Gom `bot_template.py`, bot mau Heuristic, va `local_arena.py` de sinh vien tu test 2 bot dau nhau tren may ca nhan).
  - *Verification*: Chay `pytest tests/test_starter_kit.py` -> 13/13 tests PASS.

---

## Milestone 2: Match Runner & Queue Xu Ly Tran Dau (Phu trach: Member 2)
- [x] **Task 2.1**: Viet Runner chay tran dau trong `engine/runner.py` (Chay tung bot qua tien trinh con, timeout 1.0s/turn, xu thua neu crash hoac tra ve nuoc di khong hop le).
  - *Verification*: Chay `pytest tests/test_runner.py` -> 12/12 tests PASS.
- [x] **Task 2.2**: Co che ghi file Replay JSON (`replays/match_<id>.json`) day du thong tin ban co tung luot.
  - *Verification*: Sinh file JSON voi day du snapshot, moves, va SAN notation.
- [x] **Task 2.3**: Tich hop hang doi tran dau bat dong bo (Background Queue) trong `server/queue.py`.
  - *Verification*: `execute_match_job` xu ly background task an toan, doc lap transaction.

---

## Milestone 3: Server API, Database & Quan Ly Giai Dau (Phu trach: Member 3)
- [x] **Task 3.1**: Thiet ke CSDL SQLite voi SQLAlchemy trong `server/models.py` (`User`, `Bot`, `Match`, `TournamentSetting`, `BracketMatch`).
  - *Verification*: Chay `pytest tests/test_database.py` -> 11/11 tests PASS.
- [x] **Task 3.2**: Xay dung API nop bot (`POST /api/bots/upload`) co kiem tra AST sandbox truoc khi luu.
  - *Verification*: Da kiem thu qua `tests/test_api.py`.
- [x] **Task 3.3**: Xay dung logic tinh diem Elo hang ngay (ap dung he so x) va API bang xep hang trong `server/tournament.py`.
  - *Verification*: Chay `pytest tests/test_tournament.py` -> 18/18 tests PASS.
- [x] **Task 3.4**: Xay dung thuat toan boc tham va dieu phoi giai dau Bracket ngay n+1 (Top 8/16 BO3).
  - *Verification*: Boc tham chia cap chuan xac, tinh diem chung ket chuan.

---

## Milestone 4: Giao Dien Web & Trinh Chieu Replay (Phu trach: Member 4)
- [x] **Task 4.1**: Thiet lap giao dien tinh va Jinja2 templates (Navbar, Bang xep hang Elo, Trang ca nhan).
  - *Verification*: Chay `pytest tests/test_web.py` -> 10/10 tests PASS.
- [x] **Task 4.2**: Xay dung Trinh Chieu Replay tuong tac 9x9 trong `web/static/js/visualizer.js` (Ke thua tu `resources/HTML-game-project-main`).
  - *Verification*: Giao dien ban co 9x9 muot ma, day du nut Play/Pause/Scrubber slider/Toc do.
- [x] **Task 4.3**: Trang nop code bot va xem lich su thi dau cua tung nguoi choi (`profile.html`).
  - *Verification*: Form keo tha bot, thong bao loi sandbox, danh sach bot ca nhan va lich su dau.
- [x] **Task 4.4**: Trang Quan Tri Giai Dau (`admin.html`) cho phep bat/tat cong dau, chinh he so x, va bam nut tao giai Bracket.
  - *Verification*: Cau hinh cap nhat tuc thoi vao DB va chi phoi toan bo giai.

---

## Milestone 5: Ghep Noi He Thong & Kiem Thu Toan Dien (Ca Nhom)
- [x] **Task 5.1**: Ghep noi luong End-to-End (`tests/test_e2e.py`): Dang ky -> Nop bot -> Thach dau FFA -> Server chay ngam -> Cap nhat Elo -> Xem replay -> Boc tham Bracket.
  - *Verification*: Chay `pytest tests/test_e2e.py` -> 6/6 tests PASS.
- [x] **Task 5.2**: Entrypoint 1 lenh duy nhat (`main.py`):
  - *Verification*: Khoi chay server tai `http://localhost:8000` voi day du tai khoan `admin` / `admin123`.

---

## Milestone 6: Trien Khai Da May (LAN), Bao Mat Single-Admin & Phan Tang Tai Lieu (Ca Nhom)
- [x] **Task 6.1**: Bao mat Single-Admin & cau hinh dong qua bien moi truong (`server/routes/auth.py`, `main.py`). Chan dang ky `admin`, tu dong demote admin gia mao.
  - *Verification*: Chay `pytest tests/test_admin_security.py` -> 2/2 tests PASS.
- [x] **Task 6.2**: Tu dong do IP mang LAN & banner da may (`main.py`). Hien thi `http://<LAN_IP>:8000` tren console khoi dong.
  - *Verification*: Chay `pytest tests/test_lan_banner.py` -> 2/2 tests PASS.
- [x] **Task 6.3**: Bien soan bo tai lieu chuyen biet phuc vu tung doi tuong:
  - `docs/ARCHITECTURE.md` (Dac ta kien truc 4 tang, AST sandbox, Subprocess runner, SQLite WAL).
  - `docs/BOT_GUIDE.md` (Cam nang thi sinh, luat co 9x9, API `get_move`, test offline voi `local_arena.py`).
  - `docs/ADMIN_GUIDE.md` (Cam nang ban to chuc, mang LAN, cai firewall, he so x, bracket BO3).
- [x] **Task 6.4**: Tinh gon `README.md` lam Entry Point duy nhat, ban do chi muc dieu huong (Index Directory) va FAQ.
- *Lien ket chi tiet Spec & Plan*:
  - Spec: [`docs/superpowers/specs/2026-10-09-multi-machine-single-admin-docs-design.md`](docs/superpowers/specs/2026-10-09-multi-machine-single-admin-docs-design.md)
  - Plan: [`docs/superpowers/plans/2026-10-09-multi-machine-single-admin-docs.md`](docs/superpowers/plans/2026-10-09-multi-machine-single-admin-docs.md)

---

## Milestone 7: Deep Testing Matrix & Edge-Case Security Hardening (Ca Nhom)
- [x] **Task 7.1**: Domain 1 Game Engine Extremes (`tests/test_deep_engine.py`): Bien toa do am, chan quan dong minh, chan tan cong quan cung cap/ha cap, uu tien cham dich tren turn 200, phat hien the co hoa/be tac khong co nuoc di, va kiem tra tu choi toa do khong phai so nguyen.
- [x] **Task 7.2**: Domain 2 AST Sandbox Exploits (`tests/test_deep_sandbox.py`, `engine/sandbox.py`): Va lo hong Reflection (`__class__`, `__mro__`, `__dict__`, `__base__`, `setattr`, `delattr`, `__subclasshook__`, `__init_subclass__`), chan AST recursion bombs, chan dunder byte-escapes, va xu ly cu phap loi.
- [x] **Task 7.3**: Domain 3 Subprocess Runner Traps (`tests/test_deep_runner.py`): Ep timeout xu phat vong lap vo tan `while True:`, chan bot goi `SystemExit`, xu ly an toan du lieu nuoc di bat thuong (None, string, float, tuple sai kich thuoc), bay bung no bo nho (memory bomb), va bao toan tinh bat bien cua ban co authoritative.
- [x] **Task 7.4**: Domain 4 Concurrency & Data Integrity (`tests/test_deep_concurrency.py`): Kiem tra truy cap dong thoi da luong tren SQLite WAL khong bi race condition/lock, chan san Elo khong bao gio am (clamped at 0), kiem tra an toan SQL injection trong username voi fixture CSDL cach ly hoan toan.
- [x] **Task 7.5**: Domain 5 Tournament Edge Cases (`tests/test_deep_tournament.py`, `server/tournament.py`): Xu ly boc tham so luong thi sinh le (3, 5, 7 nguoi), kiem tra hoi tu Elo khi chenh lech diem cuc lon (50 vs 3000), chan he so nhan am gay dao nguoc thang thua (`safe_multiplier = max(0.0, float(multiplier))`), va tinh diem tong ket ket hop.
- [x] **Task 7.6**: Domain 6 REST API & Access Security (`tests/test_deep_api_security.py`): Chan truy cap admin trai phep (401/403), tu choi session token gia mao, tra loi 404 sach khi replay khong ton tai, tu choi file bot upload vuot qua dung luong (>5MB payload), chan tu thach dau chinh minh, va don dep moi truong CSDL tu dong (zero state pollution).
- *Verification*: Full test suite `pytest -v` -> 203/203 tests PASS (100% Green in 11.32s).
- *Lien ket chi tiet Spec & Plan*:
  - Spec: [`docs/superpowers/specs/2026-10-09-deep-testing-matrix-design.md`](docs/superpowers/specs/2026-10-09-deep-testing-matrix-design.md)
  - Plan: [`docs/superpowers/plans/2026-10-09-deep-testing-matrix.md`](docs/superpowers/plans/2026-10-09-deep-testing-matrix.md)

---

## Milestone 8: Professional Minimalist UI, Boss Arena & Dynamic Schedule Management (Ca Nhom)
- [x] **Task 8.1**: Professional Minimalist UI Redesign (`web/static/css/style.css`, `web/static/js/visualizer.js`, `tests/test_web.py`).
  - Thiet lap bang mau Slate/Charcoal toi gian voi CSS design tokens (`--bg-main: #0d1117`, `--bg-surface: #161b22`, `--border-subtle: #30363d`, `--text-primary: #f0f6fc`, `--text-muted: #8b949e`), loai bo gradient mau me, nang cap transport bar va vien ban co phang net.
  - *Verification*: `pytest tests/test_web.py` -> 11/11 tests PASS.
- [x] **Task 8.2**: Admin Access Control and Navigation Hardening (`web/templates/base.html`, `server/main.py`, `tests/test_admin_security.py`).
  - Ap dung authorization guard cho route `/admin`: chuyen huong HTTP 303 Redirect ve `/login?next=/admin` neu chua dang nhap, tra ve HTTP 403 Forbidden neu khong phai admin; conditional rendering lien ket Admin tren navbar.
  - *Verification*: `pytest tests/test_admin_security.py` -> 4/4 tests PASS.
- [x] **Task 8.3**: Dynamic Web-Based Tournament Schedule Configuration (`server/tournament.py`, `server/routes/admin.py`, `web/templates/admin.html`, `tests/test_admin_schedule.py`).
  - Luu tru va danh gia lich trinh dong qua bang CSDL `TournamentSetting` (`start_time`, `end_time`, `ffa_mode`), xu ly khung gio trong ngay va xuyen dem, dieu khien truc tiep tren Admin portal ma khong can khoi dong lai server.
  - *Verification*: `pytest tests/test_admin_schedule.py` -> 13/13 tests PASS.
- [x] **Task 8.4**: Implementation of Five Server-Side Boss Benchmark Bots (`server/bosses/`, `tests/test_boss_bots.py`).
  - Xay dung 5 bot benchmark chuan muc server-side dat tieu chuan AST sandbox: `novice_bot.py` (Level 1: opportunistic), `rusher_bot.py` (Level 2: Chebyshev sprinter), `sentinel_bot.py` (Level 3: perimeter defense & wipeout hunter), `tactician_bot.py` (Level 4: 2-ply Minimax Alpha-Beta), va `apex_bot.py` (Level 5: adaptive dynamic-depth Minimax baiting).
  - *Verification*: `pytest tests/test_boss_bots.py` -> 11/11 tests PASS.
- [x] **Task 8.5**: Admin Boss Deployment API and Web Integration (`server/boss_manager.py`, `server/routes/admin.py`, `web/templates/admin.html`, `tests/test_admin_boss_deployment.py`).
  - Module `boss_manager.py` dong bo tai khoan va bot vao CSDL; cung cap API `GET /api/admin/bosses` va `POST /api/admin/bosses/deploy`; giao dien quan tri Boss Arena voi the card truc quan va nut bam Deploy / Retract.
  - *Verification*: `pytest tests/test_admin_boss_deployment.py` -> 5/5 tests PASS.
- [x] **Task 8.6**: Documentation Harmonization in Clean Professional Tone Without Icons (`docs/CONTEXT_RESUME.md`, `docs/ARCHITECTURE.md`, `docs/BOT_GUIDE.md`, `docs/ADMIN_GUIDE.md`, `README.md`, `TASKS.md`, `tests/test_documentation_integrity.py`).
  - Dong bo toan dien SSOT va tat ca cam nang theo giong van hoc thuat chuyen nghiep, loai bo 100% bieu tuong trang tri (icons/emojis), bo sung chi tiet kien truc 5 Boss bot, cau hinh lich trinh dong va huong dan thuat toan Minimax.
  - *Verification*: `pytest tests/test_documentation_integrity.py` -> 12/12 tests PASS.
- *Lien ket chi tiet Spec & Plan*:
  - Spec: [`docs/superpowers/specs/2026-10-09-pro-ui-boss-arena-admin-config-design.md`](docs/superpowers/specs/2026-10-09-pro-ui-boss-arena-admin-config-design.md)
  - Plan: [`docs/superpowers/plans/2026-10-09-pro-ui-boss-arena-admin-config.md`](docs/superpowers/plans/2026-10-09-pro-ui-boss-arena-admin-config.md)
