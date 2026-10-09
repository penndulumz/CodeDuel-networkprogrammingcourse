# Battlecode RPS 9x9 — Master Context Resume for AI Agents & Team

> **Mục đích của file này**: Đây là file "bộ nhớ ngữ cảnh trung tâm" (Single Source of Truth).
> Khi bất kỳ thành viên nào trong nhóm (Member 1, 2, 3, 4) làm việc với bất kỳ AI nào (Claude 3.7/Sonnet, Gemini Pro/Flash, GPT-4o, Cursor AI, DeepSeek...), hãy nạp file này vào để AI ngay lập tức nắm được 100% kiến trúc, quy ước và nhiệm vụ mà không bị quên hoặc làm sai lệch hệ thống.

---

## 1. Tóm Tắt Dự Án (System Overview)
- **Tên dự án**: Battlecode RPS Chess 9x9 Platform.
- **Mô tả**: Nền tảng thi đấu cờ Oẳn Tù Tì (Rock-Paper-Scissors) kích thước 9×9 cho sinh viên. Sinh viên viết bot bằng Python để điều khiển các quân cờ đấu 1v1.
- **Mô hình máy chủ**: Centralized Runner. Người chơi upload file bot Python lên web. Server lưu mã nguồn kín đáo (chống lộ code), chạy ngầm trận đấu, xuất file replay JSON và cập nhật điểm Elo.
- **Thể thức giải đấu**:
  - **Ngày 1 đến Ngày $n$**: Mở cổng theo khung giờ cố định (19h - 21h). Đấu tự do FFA không giới hạn. Mỗi ngày có một hệ số nhân Elo ngẫu nhiên $x \in [1.0, 3.0]$.
  - **Ngày $n+1$**: Đấu bảng loại trực tiếp (Bracket BO3) giữa các top bot để tìm nhà vô địch.
  - **Điểm tổng kết**: Kết hợp giữa Elo tích lũy và thứ hạng giải đấu ngày cuối.
- **Tech Stack**:
  - **Backend & Engine**: Python 3.10+, FastAPI, SQLite (qua SQLAlchemy), PyYAML.
  - **Frontend**: HTML5, Vanilla JavaScript, CSS (kế thừa từ `resources/HTML-game-project-main`), không dùng Node.js/npm.
  - **Deployment**: Local-First (`python main.py`), mở rộng mạng qua `cloudflared tunnel`.

---

## 2. Luật Game Oẳn Tù Tì 9×9 & Bot Interface

### 2.1 Bàn cờ và Tọa độ
- Bàn cờ 9×9: `row`: 0 đến 8 (tương ứng Rank 1 đến 9), `col`: 0 đến 8 (tương ứng File a đến i).
- Các quân cờ: `'R'` (Đấm ✊), `'P'` (Lá ✋), `'S'` (Kéo ✌).
- Khắc chế: `R > S`, `S > P`, `P > R`. Cùng loại thì chặn nhau. Thua RPS thì không được đi vào.
- **Bố trí xuất phát**:
  - Player 1 (Đỏ): Hàng 0 (rank 1) gồm `['R','R','R','P','P','P','S','S','S']`. Ô đích cần đến: `i9` (`row=8, col=8`).
  - Player 2 (Xanh): Hàng 8 (rank 9) gồm `['S','S','S','P','P','P','R','R','R']`. Ô đích cần đến: `a1` (`row=0, col=0`).
- **Nước đi**: Đi 1 ô theo 8 hướng (như quân Vua trong cờ vua).
- **Thắng**: Chạm ô đích của đối thủ HOẶC diệt sạch cả 3 quân của 1 loại (R, P, hoặc S) của đối thủ.
- **Timeout**: Tối đa 1.0 giây/turn. Tối đa 200 turns/trận.

### 2.2 Bot Python Interface (`bot.py`)
Mọi bot sinh viên viết phải có signature sau:

```python
def get_move(board: list[list[dict | None]], my_player: int, history: list[dict]) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    Args:
        board: 9x9 list where board[row][col] is None or {'type': 'R'|'P'|'S', 'player': 1|2}
        my_player: 1 or 2
        history: list of past moves [{'player': 1, 'from': (0, 0), 'to': (1, 1), 'san': '...'}]
    
    Returns:
        ((from_row, from_col), (to_row, to_col))
    """
```

---

## 3. Cấu Trúc File Replay JSON (`replays/match_<id>.json`)
Mỗi trận đấu sau khi kết thúc sẽ sinh file replay chuẩn:

```json
{
  "match_id": 101,
  "player1": {"id": 1, "username": "alice", "bot_name": "DragonV1"},
  "player2": {"id": 2, "username": "bob", "bot_name": "TitanV2"},
  "winner": 1,
  "win_reason": "goal", 
  "total_turns": 35,
  "created_at": "2026-10-08T20:30:00",
  "moves": [
    {
      "turn": 1,
      "player": 1,
      "from": [0, 3],
      "to": [1, 3],
      "piece": "P",
      "captured": null,
      "san": "✋d1-d2"
    }
  ]
}
```

---

## 4. Phân Chia Công Việc 4 Thành Viên (Roles & Responsibilities)

1. **Member 1 (Engine Lead)**:
   - Quản lý: `engine/game.py`, `engine/sandbox.py`, `starter_kit/`, `tests/test_game.py`.
   - Nhiệm vụ: Xây dựng luật cờ, kiểm tra di chuyển hợp lệ, sandbox AST chặn mã độc, bộ starter kit cho sinh viên tự test máy nhà.
2. **Member 2 (Execution Lead)**:
   - Quản lý: `engine/runner.py`, `server/queue.py`, `tests/test_runner.py`.
   - Nhiệm vụ: Chạy ván đấu giữa 2 file bot, giám sát tiến trình con, timeout 1s, bắt lỗi crash, tạo file `replay_<id>.json`.
3. **Member 3 (Backend & Tournament Lead)**:
   - Quản lý: `server/models.py`, `server/routes/`, `server/tournament.py`, `config/tournament.yaml`.
   - Nhiệm vụ: API xác thực, lưu bot, hàng đợi thách đấu FFA, công thức tính Elo nhân hệ số $x$, bốc thăm bảng Bracket ngày $n+1$.
4. **Member 4 (Frontend & Visualizer Lead)**:
   - Quản lý: `web/templates/`, `web/static/js/visualizer.js`, `web/static/css/`.
   - Nhiệm vụ: Bảng xếp hạng Elo (Leaderboard), trang hồ sơ người chơi & nộp code, visualizer bàn cờ 9×9 xem replay mượt mà, trang admin.

---

## 5. Quy Ước Lập Trình Bắt Buộc (Coding Standards)
1. **Comment**: Bắt buộc comment code bằng **Tiếng Anh rõ ràng, dễ hiểu**. Giải thích vì sao làm vậy ở các logic phức tạp.
2. **Không tự ý thêm thư viện ngoài**: Ưu tiên thư viện chuẩn của Python (`math`, `random`, `json`, `ast`, `subprocess`, `dataclasses`). Thư viện ngoài chỉ dùng những gói đã có trong `requirements.txt`.
3. **An toàn & Kiểm thử (TDD)**: Viết hàm nào phải có unit test kiểm thử hàm đó trong thư mục `tests/`.
4. **Human-in-the-loop**: Khi AI tạo code, thành viên phải tự chạy lệnh kiểm tra trên terminal máy mình trước khi cập nhật `TASKS.md` và `git commit`.

---

## 6. Master Prompts Dành Cho Thành Viên Sao Chép Cho AI

### Master Prompt 1: Khởi đầu một phiên làm việc mới
> *"Chào AI, tôi là **Member [Điền 1, 2, 3 hoặc 4]** trong nhóm phát triển dự án **Battlecode RPS 9x9**. Dự án đang tổ chức theo tài liệu `docs/CONTEXT_RESUME.md` và `TASKS.md`. Hãy đọc 2 file đó để nắm rõ toàn bộ kiến trúc hệ thống, các interface chuẩn và quy ước lập trình. Bây giờ, tôi cần bạn hỗ trợ tôi thực hiện **Task [Điền mã task, ví dụ 1.2]** trong `TASKS.md`. Hãy giải thích ngắn gọn, trực quan và viết code chuẩn với comment tiếng Anh chi tiết."*

### Master Prompt 2: Nhờ AI debug lỗi
> *"AI ơi, tôi gặp lỗi này khi chạy lệnh kiểm thử [Điền lệnh, ví dụ: pytest tests/test_game.py]: [Paste log lỗi vào đây]. Hãy đối chiếu với luật game và interface trong `docs/CONTEXT_RESUME.md` để tìm nguyên nhân gốc rễ và sửa code giúp tôi một cách tối giản nhất."*


---

## 7. Quy Tắc Vòng Lặp & Quản Lý Breaking Changes (Continuous Feedback Loop Law)

> ⚠️ **LUẬT BẮT BUỘC CHO MỌI THÀNH VIÊN VÀ MỌI AI AGENT**:
> Dự án vận hành theo mô hình **Vòng lặp phát triển khép kín (Continuous Feedback Loop)**. 

1. **Nguồn Chân Lý Duy Nhất (Single Source of Truth - SSOT)**:
   - File `docs/CONTEXT_RESUME.md` này là **NGUỒN SỰ THẬT TỐI CAO DUY NHẤT** chi phối toàn bộ kiến trúc, CSDL, luật cờ, và workflow của dự án.
   - Các file thiết lập riêng cho AI (như `GEMINI.md`, `CLAUDE.md`, `.cursorrules`...) **TUYỆT ĐỐI KHÔNG ĐƯỢC TỰ Ý ĐỊNH NGHĨA RULES MỚI HOẶC TÁCH NHÁNH QUY ƯỚC**. Chúng phải luôn trỏ về `docs/CONTEXT_RESUME.md`.
2. **Quy Tắc Cập Nhật Breaking Changes Ngay Lập Tức**:
   - Khi có bất kỳ thay đổi mang tính bước ngoặt (Breaking Change) nào — bao gồm: thay đổi API endpoint, thay đổi hàm `get_move()`, sửa đổi luật game, thay đổi schema database trong `server/models.py`, đổi port hoặc workflow — người hoặc AI thực hiện **BẮT BUỘC PHẢI CẬP NHẬT TRỰC TIẾP VÀO FILE NÀY (`docs/CONTEXT_RESUME.md`) VÀ `TASKS.md` TRONG CÙNG COMMIT ĐÓ**.
3. **Bảo Toàn Chu Trình Cho Người Đến Sau**:
   - Nếu ai đó thay đổi hệ thống mà không cập nhật `docs/CONTEXT_RESUME.md`, phiên làm việc tiếp theo của các AI khác (Claude, Gemini, Cursor) sẽ đọc dữ liệu cũ, gây ra xung đột phiên bản và phá vỡ tính liên tục của dự án. Mọi thay đổi không ghi vào đây đều bị coi là không hợp lệ.

---

## 8. Quy Tắc Bắt Buộc Cách Ly Bằng Git Worktrees (Mandatory Git Worktree Isolation)
1. **Luôn dùng Worktree khi phát triển tính năng mới**:
   - Mọi task mới hoặc refactor lớn bắt buộc phải tạo nhánh cách ly trong thư mục `.worktrees/<tên-nhánh>` thông qua kỹ năng `using-git-worktrees`.
   - Tuyệt đối không code trực tiếp lên nhánh `main` khi chưa hoàn thành TDD và được review toàn diện.
2. **Quy trình kết thúc nhánh**:
   - Chỉ merge về `main` sau khi toàn bộ test suite (`pytest -v`) đạt 100% PASS và thực hiện clean up worktree đúng chuẩn.

---

## 9. Bảo Tồn Tuyệt Đối Thư Mục Gốc & File Meta (Root Preservation Law)
1. **Thư mục `resources/` (Thư viện tham khảo của User)**:
   - `resources/` là thư mục chứa tài liệu gốc và các dự án mẫu của User, đã được đưa vào `.gitignore`.
   - **BẤT BIẾN**: `resources/` CHỈ NẰM DUY NHẤT TẠI THƯ MỤC GỐC (ROOT REPO). Tuyệt đối không di chuyển, không xóa và KHÔNG ĐƯỢC DUPLICATE/COPY vào bên trong các worktree `.worktrees/`.
2. **Các thư mục và file meta**:
   - `.git/`, `.gemini/`, `GEMINI.md`, `CLAUDE.md`, và `docs/CONTEXT_RESUME.md` luôn giữ nguyên vị trí chuẩn ở root.

---

## 10. Nguyên Tắc Single-Admin & Triển Khai Đa Máy (Multi-Machine LAN)
1. **Duy Nhất Một Tài Khoản Quản Trị (Single-Admin Invariant)**:
   - Hệ thống chỉ cho phép đúng **1 tài khoản Admin tối cao**.
   - Cấu hình qua biến môi trường: `ADMIN_USERNAME` (mặc định: `admin`), `ADMIN_PASSWORD` (mặc định: `admin123`).
   - Mọi nỗ lực đăng ký tài khoản mang tên `admin` (hoặc trùng `ADMIN_USERNAME`, không phân biệt hoa thường) đều bị API từ chối với mã lỗi HTTP 400.
   - Khi khởi động seeder, bất kỳ tài khoản nào khác có `is_admin = True` đều tự động bị hạ quyền xuống `is_admin = False`.
2. **Triển Khai Đa Máy Qua Mạng Nội Bộ (LAN Access)**:
   - Server lắng nghe trên mọi giao diện mạng (`0.0.0.0:8000`).
   - Banner khởi động tự động dò IP mạng nội bộ của máy chủ (`http://<LAN_IP>:8000`) để người tổ chức cung cấp cho các máy tính khác trong cùng Wi-Fi/LAN truy cập thi đấu.

