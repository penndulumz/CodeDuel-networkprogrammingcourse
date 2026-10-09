# Kế Hoạch Thực Hiện & Theo Dõi Tiến Độ Dự Án (TASKS.md)

> **Trạng thái**: 🎉 **100% HOÀN THÀNH VÀ TOÀN BỘ TEST PASS (203/203 tests passed in 11.32s)**
> - Quy tắc: Đã kiểm chứng tự động toàn diện qua Subagent-Driven Development, 6-domain Deep Testing Matrix, và Unit/Integration/E2E test suite.

---

## 🎯 Milestone 0: Khởi Tạo Dự Án & Môi Trường Chung (Cả Nhóm)
- [x] **Task 0.1**: Tạo file `requirements.txt` với các thư viện cốt lõi (`fastapi`, `uvicorn`, `sqlalchemy`, `pyyaml`, `jinja2`, `python-multipart`, `pytest`).
  - *Verification*: Đã cài đặt và kiểm tra trên Python 3.13 / 3.10+.
- [x] **Task 0.2**: Tạo file cấu hình mẫu `config/tournament.yaml`.
  - *Verification*: Đọc được file bằng PyYAML không bị lỗi cú pháp (`load_tournament_config`).

---

## 🧩 Milestone 1: Core Engine & Bot Starter Kit (Phụ trách: Member 1)
- [x] **Task 1.1**: Viết Game Logic 9×9 trong `engine/game.py` (Bàn cờ, quân R/P/S, luật ăn quân, kiểm tra chạm đích i9/a1, kiểm tra diệt sạch quân).
  - *Verification*: Chạy `pytest tests/test_game.py` -> 17/17 tests PASS.
- [x] **Task 1.2**: Viết bộ lọc bảo mật AST trong `engine/sandbox.py` (Phát hiện và cấm import `os`, `sys`, `socket`, `open`, `eval`...).
  - *Verification*: Chạy `pytest tests/test_sandbox.py` -> 74/74 tests PASS.
- [x] **Task 1.3**: Xây dựng gói `starter_kit/` (Gồm `bot_template.py`, bot mẫu Heuristic, và `local_arena.py` để sinh viên tự test 2 bot đấu nhau trên máy cá nhân).
  - *Verification*: Chạy `pytest tests/test_starter_kit.py` -> 13/13 tests PASS.

---

## ⚡ Milestone 2: Match Runner & Queue Xử Lý Trận Đấu (Phụ trách: Member 2)
- [x] **Task 2.1**: Viết Runner chạy trận đấu trong `engine/runner.py` (Chạy từng bot qua tiến trình con, timeout 1.0s/turn, xử thua nếu crash hoặc trả về nước đi không hợp lệ).
  - *Verification*: Chạy `pytest tests/test_runner.py` -> 12/12 tests PASS.
- [x] **Task 2.2**: Cơ chế ghi file Replay JSON (`replays/match_<id>.json`) đầy đủ thông tin bàn cờ từng lượt.
  - *Verification*: Sinh file JSON với đầy đủ snapshot, moves, và SAN notation.
- [x] **Task 2.3**: Tích hợp hàng đợi trận đấu bất đồng bộ (Background Queue) trong `server/queue.py`.
  - *Verification*: `execute_match_job` xử lý background task an toàn, độc lập transaction.

---

## 🗄️ Milestone 3: Server API, Database & Quản Lý Giải Đấu (Phụ trách: Member 3)
- [x] **Task 3.1**: Thiết kế CSDL SQLite với SQLAlchemy trong `server/models.py` (`User`, `Bot`, `Match`, `TournamentSetting`, `BracketMatch`).
  - *Verification*: Chạy `pytest tests/test_database.py` -> 11/11 tests PASS.
- [x] **Task 3.2**: Xây dựng API nộp bot (`POST /api/bots/upload`) có kiểm tra AST sandbox trước khi lưu.
  - *Verification*: Đã kiểm thử qua `tests/test_api.py`.
- [x] **Task 3.3**: Xây dựng logic tính điểm Elo hàng ngày (áp dụng hệ số $x$) và API bảng xếp hạng trong `server/tournament.py`.
  - *Verification*: Chạy `pytest tests/test_tournament.py` -> 18/18 tests PASS.
- [x] **Task 3.4**: Xây dựng thuật toán bốc thăm và điều phối giải đấu Bracket ngày $n+1$ (Top 8/16 BO3).
  - *Verification*: Bốc thăm chia cặp chuẩn xác, tính điểm chung kết chuẩn.

---

## 🎨 Milestone 4: Giao Diện Web & Trình Chiếu Replay (Phụ trách: Member 4)
- [x] **Task 4.1**: Thiết lập giao diện tĩnh và Jinja2 templates (Navbar, Bảng xếp hạng Elo, Trang cá nhân).
  - *Verification*: Chạy `pytest tests/test_web.py` -> 10/10 tests PASS.
- [x] **Task 4.2**: Xây dựng Trình Chiếu Replay tương tác 9×9 trong `web/static/js/visualizer.js` (Kế thừa từ `resources/HTML-game-project-main`).
  - *Verification*: Giao diện bàn cờ 9×9 mượt mà, đầy đủ nút Play/Pause/Scrubber slider/Tốc độ.
- [x] **Task 4.3**: Trang nộp code bot và xem lịch sử thi đấu của từng người chơi (`profile.html`).
  - *Verification*: Form kéo thả bot, thông báo lỗi sandbox, danh sách bot cá nhân và lịch sử đấu.
- [x] **Task 4.4**: Trang Quản Trị Giải Đấu (`admin.html`) cho phép bật/tắt cổng đấu, chỉnh hệ số $x$, và bấm nút tạo giải Bracket.
  - *Verification*: Cấu hình cập nhật tức thời vào DB và chi phối toàn bộ giải.

---

## 🚀 Milestone 5: Ghép Nối Hệ Thống & Kiểm Thử Toàn Diện (Cả Nhóm)
- [x] **Task 5.1**: Ghép nối luồng End-to-End (`tests/test_e2e.py`): Đăng ký -> Nộp bot -> Thách đấu FFA -> Server chạy ngầm -> Cập nhật Elo -> Xem replay -> Bốc thăm Bracket.
  - *Verification*: Chạy `pytest tests/test_e2e.py` -> 6/6 tests PASS.
- [x] **Task 5.2**: Entrypoint 1 lệnh duy nhất (`main.py`):
  - *Verification*: Khởi chạy server tại `http://localhost:8000` với đầy đủ tài khoản `admin` / `admin123`.

---

## 🌐 Milestone 6: Triển Khai Đa Máy (LAN), Bảo Mật Single-Admin & Phân Tầng Tài Liệu (Cả Nhóm)
- [x] **Task 6.1**: Bảo mật Single-Admin & cấu hình động qua biến môi trường (`server/routes/auth.py`, `main.py`). Chặn đăng ký `admin`, tự động demote admin giả mạo.
  - *Verification*: Chạy `pytest tests/test_admin_security.py` -> 2/2 tests PASS.
- [x] **Task 6.2**: Tự động dò IP mạng LAN & banner đa máy (`main.py`). Hiển thị `http://<LAN_IP>:8000` trên console khởi động.
  - *Verification*: Chạy `pytest tests/test_lan_banner.py` -> 2/2 tests PASS.
- [x] **Task 6.3**: Biên soạn bộ tài liệu chuyên biệt phục vụ từng đối tượng:
  - `docs/ARCHITECTURE.md` (Đặc tả kiến trúc 4 tầng, AST sandbox, Subprocess runner, SQLite WAL).
  - `docs/BOT_GUIDE.md` (Cẩm nang thí sinh, luật cờ 9×9, API `get_move`, test offline với `local_arena.py`).
  - `docs/ADMIN_GUIDE.md` (Cẩm nang ban tổ chức, mạng LAN, cài firewall, hệ số $x$, bracket BO3).
- [x] **Task 6.4**: Tinh gọn `README.md` làm Entry Point duy nhất, bản đồ chỉ mục điều hướng (Index Directory) và FAQ.
- *Liên kết chi tiết Spec & Plan*:
  - Spec: [`docs/superpowers/specs/2026-10-09-multi-machine-single-admin-docs-design.md`](docs/superpowers/specs/2026-10-09-multi-machine-single-admin-docs-design.md)
  - Plan: [`docs/superpowers/plans/2026-10-09-multi-machine-single-admin-docs.md`](docs/superpowers/plans/2026-10-09-multi-machine-single-admin-docs.md)

---

## 🛡️ Milestone 7: Deep Testing Matrix & Edge-Case Security Hardening (Cả Nhóm)
- [x] **Task 7.1**: Domain 1 Game Engine Extremes (`tests/test_deep_engine.py`): Biên tọa độ âm, chặn quân đồng minh, chặn tấn công quân cùng cấp/hạ cấp, ưu tiên chạm đích trên turn 200, phát hiện thế cờ hòa/bế tắc không có nước đi, và kiểm tra từ chối tọa độ không phải số nguyên.
- [x] **Task 7.2**: Domain 2 AST Sandbox Exploits (`tests/test_deep_sandbox.py`, `engine/sandbox.py`): Vá lỗ hổng Reflection (`__class__`, `__mro__`, `__dict__`, `__base__`, `setattr`, `delattr`, `__subclasshook__`, `__init_subclass__`), chặn AST recursion bombs, chặn dunder byte-escapes, và xử lý cú pháp lỗi.
- [x] **Task 7.3**: Domain 3 Subprocess Runner Traps (`tests/test_deep_runner.py`): Ép timeout xử phạt vòng lặp vô tận `while True:`, chặn bot gọi `SystemExit`, xử lý an toàn dữ liệu nước đi bất thường (None, string, float, tuple sai kích thước), bẫy bùng nổ bộ nhớ (memory bomb), và bảo toàn tính bất biến của bàn cờ authoritative.
- [x] **Task 7.4**: Domain 4 Concurrency & Data Integrity (`tests/test_deep_concurrency.py`): Kiểm tra truy cập đồng thời đa luồng trên SQLite WAL không bị race condition/lock, chặn sàn Elo không bao giờ âm (clamped at 0), kiểm tra an toàn SQL injection trong username với fixture CSDL cách ly hoàn toàn.
- [x] **Task 7.5**: Domain 5 Tournament Edge Cases (`tests/test_deep_tournament.py`, `server/tournament.py`): Xử lý bốc thăm số lượng thí sinh lẻ (3, 5, 7 người), kiểm tra hội tụ Elo khi chênh lệch điểm cực lớn (50 vs 3000), chặn hệ số nhân âm gây đảo ngược thắng thua (`safe_multiplier = max(0.0, float(multiplier))`), và tính điểm tổng kết kết hợp.
- [x] **Task 7.6**: Domain 6 REST API & Access Security (`tests/test_deep_api_security.py`): Chặn truy cập admin trái phép (401/403), từ chối session token giả mạo, trả lỗi 404 sạch khi replay không tồn tại, từ chối file bot upload vượt quá dung lượng (>5MB payload), chặn tự thách đấu chính mình, và dọn dẹp môi trường CSDL tự động (zero state pollution).
- *Verification*: Full test suite `pytest -v` -> 203/203 tests PASS (100% Green in 11.32s).
- *Liên kết chi tiết Spec & Plan*:
  - Spec: [`docs/superpowers/specs/2026-10-09-deep-testing-matrix-design.md`](docs/superpowers/specs/2026-10-09-deep-testing-matrix-design.md)
  - Plan: [`docs/superpowers/plans/2026-10-09-deep-testing-matrix.md`](docs/superpowers/plans/2026-10-09-deep-testing-matrix.md)


