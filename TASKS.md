# Kế Hoạch Thực Hiện & Theo Dõi Tiến Độ Dự Án (TASKS.md)

> **Hướng dẫn sử dụng**:
> - Mỗi thành viên phụ trách một khối công việc (Milestone).
> - Trạng thái: `[ ]` Chưa làm | `[-]` Đang làm | `[x]` Đã hoàn thành & test pass.
> - **Nguyên tắc**: Chỉ đánh dấu `[x]` sau khi bạn đã tự chạy lệnh kiểm thử (Verification) trên terminal máy mình thành công.

---

## 🎯 Milestone 0: Khởi Tạo Dự Án & Môi Trường Chung (Cả Nhóm)
- [ ] **Task 0.1**: Tạo file `requirements.txt` với các thư viện cốt lõi (`fastapi`, `uvicorn`, `sqlalchemy`, `pyyaml`, `jinja2`, `python-multipart`, `pytest`).
  - *Verification*: Chạy `pip install -r requirements.txt` không báo lỗi.
- [ ] **Task 0.2**: Tạo file cấu hình mẫu `config/tournament.yaml`.
  - *Verification*: Đọc được file bằng PyYAML không bị lỗi cú pháp.

---

## 🧩 Milestone 1: Core Engine & Bot Starter Kit (Phụ trách: Member 1)
- [ ] **Task 1.1**: Viết Game Logic 9×9 trong `engine/game.py` (Bàn cờ, quân R/P/S, luật ăn quân, kiểm tra chạm đích i9/a1, kiểm tra diệt sạch quân).
  - *Verification*: Chạy `pytest tests/test_game.py` -> All pass.
- [ ] **Task 1.2**: Viết bộ lọc bảo mật AST trong `engine/sandbox.py` (Phát hiện và cấm import `os`, `sys`, `socket`, `open`, `eval`...).
  - *Verification*: Chạy `pytest tests/test_sandbox.py` -> Bắt chính xác code độc hại.
- [ ] **Task 1.3**: Xây dựng gói `starter_kit/` (Gồm `bot_template.py`, bot mẫu Heuristic, và `local_arena.py` để sinh viên tự test 2 bot đấu nhau trên máy cá nhân).
  - *Verification*: Chạy `python starter_kit/local_arena.py` -> 2 bot đấu nhau và in kết quả ra màn hình terminal.

---

## ⚡ Milestone 2: Match Runner & Queue Xử Lý Trận Đấu (Phụ trách: Member 2)
- [ ] **Task 2.1**: Viết Runner chạy trận đấu trong `engine/runner.py` (Chạy từng bot qua tiến trình con, timeout 1.0s/turn, xử thua nếu crash hoặc trả về nước đi không hợp lệ).
  - *Verification*: Chạy `pytest tests/test_runner.py` -> Kiểm tra trường hợp bot ngủ quá 1s bị xử thua.
- [ ] **Task 2.2**: Cơ chế ghi file Replay JSON (`replays/match_<id>.json`) đầy đủ thông tin bàn cờ từng lượt.
  - *Verification*: Chạy 1 trận đấu thử và kiểm tra file `.json` sinh ra đúng format.
- [ ] **Task 2.3**: Tích hợp hàng đợi trận đấu bất đồng bộ (Background Queue) trong `server/queue.py`.
  - *Verification*: Đẩy 5 trận đấu cùng lúc vào hàng đợi, server lần lượt xử lý xong cả 5 trận không bị nghẽn.

---

## 🗄️ Milestone 3: Server API, Database & Quản Lý Giải Đấu (Phụ trách: Member 3)
- [ ] **Task 3.1**: Thiết kế CSDL SQLite với SQLAlchemy trong `server/models.py` (`User`, `Bot`, `Match`, `TournamentSetting`, `BracketMatch`).
  - *Verification*: Khởi tạo CSDL sinh ra file `app.db` với đầy đủ các bảng.
- [ ] **Task 3.2**: Xây dựng API nộp bot (`POST /api/bots/upload`) có kiểm tra AST sandbox trước khi lưu.
  - *Verification*: Gửi file bot qua API -> File được lưu an toàn vào thư mục `bots/<user_id>/`.
- [ ] **Task 3.3**: Xây dựng logic tính điểm Elo hàng ngày (áp dụng hệ số $x$) và API bảng xếp hạng trong `server/tournament.py`.
  - *Verification*: Chạy `pytest tests/test_tournament.py` -> Điểm Elo cập nhật chính xác theo công thức.
- [ ] **Task 3.4**: Xây dựng thuật toán bốc thăm và điều phối giải đấu Bracket ngày $n+1$ (Top 8/16 BO3).
  - *Verification*: Sinh bảng đấu loại trực tiếp chính xác từ danh sách Top players.

---

## 🎨 Milestone 4: Giao Diện Web & Trình Chiếu Replay (Phụ trách: Member 4)
- [ ] **Task 4.1**: Thiết lập giao diện tĩnh và Jinja2 templates (Navbar, Bảng xếp hạng Elo, Trang cá nhân).
  - *Verification*: Mở trình duyệt `http://localhost:8000` thấy bảng xếp hạng hiển thị đẹp mắt.
- [ ] **Task 4.2**: Xây dựng Trình Chiếu Replay tương tác 9×9 trong `web/static/js/visualizer.js` (Kế thừa từ `resources/HTML-game-project-main`).
  - *Verification*: Nạp file `match.json` -> Bàn cờ tự động đi từng nước, có nút Play/Pause/Tua lượt.
- [ ] **Task 4.3**: Trang nộp code bot và xem lịch sử thi đấu của từng người chơi (`profile.html`).
  - *Verification*: Upload file `.py` trên web thành công và thấy danh sách các trận đấu cũ.
- [ ] **Task 4.4**: Trang Quản Trị Giải Đấu (`admin.html`) cho phép bật/tắt cổng đấu, chỉnh hệ số $x$, và bấm nút tạo giải Bracket.
  - *Verification*: Admin bấm đổi $x = 2.5$ -> Hệ thống áp dụng ngay cho các trận tiếp theo.

---

## 🚀 Milestone 5: Ghép Nối Hệ Thống & Kiểm Thử Toàn Diện (Cả Nhóm)
- [ ] **Task 5.1**: Ghép nối luồng End-to-End: Người chơi A tạo tài khoản -> Nộp bot -> Thách đấu B -> Server chạy trận -> Cập nhật Elo -> Bấm xem Replay.
- [ ] **Task 5.2**: Kiểm thử tải với 20 bot thi đấu đồng thời trên máy local.
- [ ] **Task 5.3**: Chạy thử nghiệm qua mạng (dùng `cloudflared tunnel` để các máy khác nhau truy cập thi đấu).
