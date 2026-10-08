# Kế Hoạch Thực Hiện & Theo Dõi Tiến Độ Dự Án (TASKS.md)

> **Trạng thái**: 🎉 **100% HOÀN THÀNH VÀ TOÀN BỘ TEST PASS (167/167 tests passed in 5.88s)**
> - Quy tắc: Đã kiểm chứng tự động toàn diện qua Subagent-Driven Development và Unit/Integration/E2E test suite.

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
