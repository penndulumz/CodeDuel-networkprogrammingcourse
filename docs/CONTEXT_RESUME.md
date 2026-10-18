# Battlecode RPS 9x9 — Master Context Resume for AI Agents & Team

> **Mục đích của file này**: Đây là file "bộ nhớ ngữ cảnh trung tâm" (Single Source of Truth - SSOT).
> Khi bất kỳ thành viên nào trong nhóm (Member 1, 2, 3, 4) làm việc với bất kỳ AI nào (Claude, Gemini, GPT, Cursor AI, DeepSeek...), hãy nạp file này vào để AI ngay lập tức nắm được 100% kiến trúc, quy ước và nhiệm vụ mà không bị quên hoặc làm sai lệch hệ thống.

---

## 1. Tóm Tắt Dự Án (System Overview)
- **Tên dự án**: CodeDuel Arena (tiền thân: Battlecode RPS Chess 9x9 Platform).
- **Mô tả**: Nền tảng thi đấu bot cho sinh viên năm nhất, hỗ trợ nhiều trò chơi (Connect Four, Caro 15x15, Cờ Oẳn Tù Tì 9x9 - xem Mục 19). Sinh viên viết bot bằng Python (cùng một hàm `get_move`) để đấu 1v1.
- **Mô hình máy chủ**: Centralized Runner. Người chơi upload file bot Python lên web. Server lưu mã nguồn kín đáo (chống lộ code), chạy ngầm trận đấu trong tiến trình con cô lập, xuất file replay JSON và cập nhật điểm Elo.
- **Thể thức giải đấu**:
  - **Ngày 1 đến Ngày n**: Mở cổng theo khung giờ động được cấu hình qua cơ sở dữ liệu (mặc định 19h - 21h). Đấu tự do FFA không giới hạn. Mỗi ngày có một hệ số nhân Elo ngẫu nhiên x trong [1.0, 3.0].
  - **Ngày n+1**: Đấu bảng loại trực tiếp (Bracket BO3) giữa các top bot để tìm nhà vô địch.
  - **Điểm tổng kết**: Kết hợp giữa Elo tích lũy và thứ hạng giải đấu ngày cuối.
- **Tech Stack**:
  - **Backend & Engine**: Python 3.10+, FastAPI, SQLite (qua SQLAlchemy WAL), PyYAML.
  - **Frontend**: HTML5, Vanilla JavaScript, CSS3 Design Tokens (bảng màu tối Charcoal/Slate chuyên nghiệp), không dùng Node.js/npm.
  - **Deployment**: Local-First & Multi-Machine LAN (`python main.py` lắng nghe trên `0.0.0.0:8000` với cơ chế tự động dò IP mạng LAN `http://<LAN_IP>:8000`), không phụ thuộc dịch vụ đám mây ngoài. Mở ra Internet (WAN) bằng `python main.py --tunnel` hoặc `--public-url` (Mục 18, Mục 22).

---

## 2. Luật Game Oẳn Tù Tì 9x9 & Bot Interface

### 2.1 Bàn cờ và Tọa độ
- Bàn cờ 9x9: `row`: 0 đến 8 (tương ứng Rank 1 đến 9), `col`: 0 đến 8 (tương ứng File a đến i).
- Các quân cờ: `'R'` (Đấm / Rock), `'P'` (Lá / Paper), `'S'` (Kéo / Scissors).
- Khắc chế: `R > S`, `S > P`, `P > R`. Cùng loại thì chặn nhau. Thua RPS thì không được đi vào.
- **Bố trí xuất phát**:
  - Player 1 (Đỏ): Hàng 0 (rank 1) gồm `['R','R','R','P','P','P','S','S','S']`. Ô đích cần đến: `i9` (`row=8, col=8`).
  - Player 2 (Xanh): Hàng 8 (rank 9) gồm `['S','S','S','P','P','P','R','R','R']`. Ô đích cần đến: `a1` (`row=0, col=0`).
- **Nước đi**: Đi 1 ô theo 8 hướng (ngang, dọc, chéo như quân Vua trong cờ vua).
- **Thắng**: Chạm ô đích của đối thủ HOẶC diệt sạch cả 3 quân của 1 loại (R, P, hoặc S) của đối thủ.
- **Timeout**: Tối đa 1.0 giây/turn. Tối đa 200 turns/trận.

### 2.2 Bot Python Interface (`bot.py`)
Mỗi bot sinh viên viết phải có signature chuẩn sau:

```python
def get_move(board: list[list[dict | None]], my_player: int, history: list[dict]) -> tuple[tuple[int, int], tuple[int, int]]:
    """Calculate and return the next move for the bot.

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
Mỗi trận đấu sau khi kết thúc sẽ sinh file replay JSON có định dạng chuẩn:

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
      "san": "Pd1-d2"
    }
  ]
}
```

---

## 4. Phân Chia Công Việc 4 Thành Viên (Roles & Responsibilities)

1. **Member 1 (Engine Lead)**:
   - Quản lý: `engine/game.py`, `engine/sandbox.py`, `starter_kit/`, `tests/test_game.py`, `tests/test_sandbox.py`.
   - Nhiệm vụ: Xây dựng luật cờ, kiểm tra di chuyển hợp lệ, sandbox AST chặn mã độc (74 mẫu tấn công), bộ starter kit cho sinh viên tự test offline.
2. **Member 2 (Execution Lead)**:
   - Quản lý: `engine/runner.py`, `server/queue.py`, `tests/test_runner.py`.
   - Nhiệm vụ: Chạy ván đấu giữa 2 file bot, giám sát tiến trình con, timeout 1.0s, bắt lỗi crash, tạo file `replays/match_<id>.json`.
3. **Member 3 (Backend & Tournament Lead)**:
   - Quản lý: `server/models.py`, `server/routes/`, `server/tournament.py`, `server/boss_manager.py`, `server/bosses/`, `server/rating_history.py`, `config/tournament.yaml`.
   - Nhiệm vụ: API xác thực, lưu bot, hàng đợi thách đấu FFA, công thức tính Elo nhân hệ số x, tái thiết lập lịch sử rating và API quỹ đạo Elo, quản lý Boss Arena, bộ đánh giá lịch trình động và bốc thăm bảng Bracket.
4. **Member 4 (Frontend & Visualizer Lead)**:
   - Quản lý: `web/templates/`, `web/static/js/visualizer.js`, `web/static/js/rating_chart.js`, `web/static/css/`.
   - Nhiệm vụ: Bảng xếp hạng Elo (Leaderboard), trang hồ sơ người chơi & nộp code, visualizer bàn cờ 9x9 xem replay mượt mà với design tokens Charcoal, biểu đồ quỹ đạo rating SVG đa đường nét (RatingChart), trang quản trị admin bảo mật.

---

## 5. Quy Ước Lập Trình Bắt Buộc (Coding Standards)

1. **Comment**: Bắt buộc comment code bằng **Tiếng Anh rõ ràng, dễ hiểu**. Giải thích lý do thiết kế ở các logic phức tạp.
2. **Không tự ý thêm thư viện ngoài**: Ưu tiên thư viện chuẩn của Python (`math`, `random`, `json`, `ast`, `subprocess`, `dataclasses`). Thư viện ngoài chỉ dùng những gói đã có trong `requirements.txt`.
3. **An toàn & Kiểm thử (TDD)**: Viết hàm nào phải có unit test kiểm thử hàm đó trong thư mục `tests/`.
4. **Human-in-the-loop**: Khi AI tạo code, thành viên phải tự chạy lệnh kiểm tra trên terminal trước khi cập nhật `TASKS.md` và commit git.

---

## 6. Master Prompts Dành Cho Thành Viên Sao Chép Cho AI

### Master Prompt 1: Khởi đầu một phiên làm việc mới
> *"Tôi là **Member [Điền 1, 2, 3 hoặc 4]** trong nhóm phát triển dự án **Battlecode RPS 9x9**. Dự án đang tổ chức theo tài liệu `docs/CONTEXT_RESUME.md` và `TASKS.md`. Hãy đọc 2 file đó để nắm rõ toàn bộ kiến trúc hệ thống, các interface chuẩn và quy ước lập trình. Bây giờ, tôi cần bạn hỗ trợ tôi thực hiện **Task [Điền mã task, ví dụ 1.2]** trong `TASKS.md`. Hãy giải thích ngắn gọn, trực quan và viết code chuẩn với comment tiếng Anh chi tiết."*

### Master Prompt 2: Nhờ AI debug lỗi
> *"Tôi gặp lỗi này khi chạy lệnh kiểm thử [Điền lệnh, ví dụ: pytest tests/test_game.py]: [Paste log lỗi vào đây]. Hãy đối chiếu với luật game và interface trong `docs/CONTEXT_RESUME.md` để tìm nguyên nhân gốc rễ và sửa code giúp tôi một cách tối giản nhất."*

---

## 7. Quy Tắc Vòng Lặp & Quản Lý Breaking Changes (Continuous Feedback Loop Law)

> **QUY TẮC BẮT BUỘC CHO MỌI THÀNH VIÊN VÀ MỌI AI AGENT**:
> Dự án vận hành theo mô hình **Vòng lặp phát triển khép kín (Continuous Feedback Loop)**.

1. **Nguồn Chân Lý Duy Nhất (Single Source of Truth - SSOT)**:
   - File `docs/CONTEXT_RESUME.md` này là **NGUỒN SỰ THẬT TỐI CAO DUY NHẤT** chi phối toàn bộ kiến trúc, CSDL, luật cờ, và workflow của dự án.
   - Các file thiết lập riêng cho AI (như `GEMINI.md`, `CLAUDE.md`, `.cursorrules`...) **TUYỆT ĐỐI KHÔNG ĐƯỢC TỰ Ý ĐỊNH NGHĨA RULES MỚI HOẶC TÁCH NHÁNH QUY ƯỚC**. Chúng phải luôn trỏ về `docs/CONTEXT_RESUME.md`.
2. **Quy Tắc Cập Nhật Breaking Changes Ngay Lập Tức**:
   - Khi có bất kỳ thay đổi mang tính bước ngoặt nào — bao gồm: thay đổi API endpoint, thay đổi hàm `get_move()`, sửa đổi luật game, thay đổi schema database trong `server/models.py`, đổi port, bổ sung boss mới, hay thay đổi cấu hình lịch trình — người hoặc AI thực hiện **BẮT BUỘC PHẢI CẬP NHẬT TRỰC TIẾP VÀO FILE NÀY (`docs/CONTEXT_RESUME.md`) VÀ `TASKS.md` TRONG CÙNG COMMIT ĐÓ**.
3. **Bảo Toàn Chu Trình Cho Người Đến Sau**:
   - Nếu ai đó thay đổi hệ thống mà không cập nhật `docs/CONTEXT_RESUME.md`, phiên làm việc tiếp theo của các AI khác (Claude, Gemini, Cursor) sẽ đọc dữ liệu cũ, gây ra xung đột phiên bản và phá vỡ tính liên tục của dự án. Mọi thay đổi không ghi vào đây đều bị coi là không hợp lệ.

---

## 8. Quy Tắc Bắt Buộc Cách Ly Bằng Git Worktrees (Mandatory Git Worktree Isolation)
1. **Luôn dùng Worktree khi phát triển tính năng mới**:
   - Mỗi task mới hoặc refactor lớn bắt buộc phải tạo nhánh cách ly trong thư mục `.worktrees/<tên-nhánh>` thông qua `git worktree`.
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
2. **Kiểm Soát Truy Cập Tuyến Admin (Route Authorization Guards)**:
   - Route `/admin` yêu cầu xác thực admin nghiêm ngặt.
   - Người dùng chưa đăng nhập truy cập `/admin` sẽ bị chuyển hướng HTTP 303 Redirect về `/login?next=/admin`.
   - Người dùng đã đăng nhập nhưng không có quyền admin sẽ nhận lỗi HTTP 403 Forbidden.
   - Thanh điều hướng (navbar) chỉ hiển thị mục `Admin` khi người dùng hiện tại có `is_admin = True`.
3. **Triển Khai Đa Máy Qua Mạng Nội Bộ (LAN Access)**:
   - Server lắng nghe trên mọi giao diện mạng (`0.0.0.0:8000`).
   - Banner khởi động tự động dò IP mạng nội bộ của máy chủ (`http://<LAN_IP>:8000`) để người tổ chức cung cấp cho các máy tính khác trong cùng Wi-Fi/LAN truy cập thi đấu.

---

## 11. Đấu Trường Boss Benchmark Server-Side (`server/bosses/`, `server/boss_manager.py`)
Hệ thống cung cấp 5 bot chuẩn mực server-side (Server Bosses) đặt tại thư mục `server/bosses/` nhằm phục vụ việc test bot, đọ sức trên Leaderboard và làm mốc tham chiếu:

1. **Level 1: Novice (`novice_bot.py`)**:
   - Slug: `novice`, Display Name: `[Boss] Level 1: Novice`, Default Elo: 1000.
   - Thuật toán: Chọn ngay nước chạm đích nếu có, thực hiện ăn quân có lợi nếu có, còn lại di chuyển ngẫu nhiên hợp lệ.
2. **Level 2: Rusher (`rusher_bot.py`)**:
   - Slug: `rusher`, Display Name: `[Boss] Level 2: Rusher`, Default Elo: 1200.
   - Thuật toán: Tính khoảng cách Chebyshev tới ô đích (`i9` hoặc `a1`), ưu tiên tuyệt đối nước tiến về đích và né tránh các ô bị quân địch khắc chế đe dọa.
3. **Level 3: Sentinel (`sentinel_bot.py`)**:
   - Slug: `sentinel`, Display Name: `[Boss] Level 3: Sentinel`, Default Elo: 1400.
   - Thuật toán: Phòng thủ vành đai bảo vệ ô đích nhà, đồng thời theo dõi và tập trung tiêu diệt loại quân có số lượng ít nhất của đối thủ để giành chiến thắng Wipeout.
4. **Level 4: Tactician (`tactician_bot.py`)**:
   - Slug: `tactician`, Display Name: `[Boss] Level 4: Tactician`, Default Elo: 1600.
   - Thuật toán: Tìm kiếm Minimax 2 lớp (2-ply) với cắt tỉa Alpha-Beta. Hàm đánh giá thế trận cân bằng giữa giá trị quân cờ, khoảng cách tới ô đích, áp lực đe dọa và vị trí an toàn.
5. **Level 5: Apex Master (`apex_bot.py`)**:
   - Slug: `apex`, Display Name: `[Boss] Level 5: Apex Master`, Default Elo: 1800.
   - Thuật toán: Minimax độ sâu thích ứng động, kết hợp bẫy quân (piece baiting), phán đoán nước đi tiếp theo của đối thủ và hội tụ thế trận tấn công ép góc.

**Quản Lý Triển Khai Boss (`server/boss_manager.py`)**:
- Chỉ Admin mới có quyền triển khai (`deploy_boss`) hoặc gỡ bỏ (`retract_boss`) các Boss bot.
- Khi triển khai, hệ thống tạo tài khoản User đại diện (ví dụ: username `boss_novice`, `boss_apex`), sao chép file bot vào `bots/` và gắn bot hoạt động.
- API quản lý:
  - `GET /api/admin/bosses`: Trả về danh sách tất cả boss và trạng thái triển khai hiện tại.
  - `POST /api/admin/bosses/deploy`: Triển khai hoặc thu hồi boss dựa trên tham số `slug` và `action` (`deploy` hoặc `retract`).

---

## 12. Cấu Hình Lịch Trình Giải Đấu Động Trong CSDL (`TournamentSetting`)
Hệ thống hỗ trợ cấu hình lịch trình động lưu trữ trong bảng `TournamentSetting` của CSDL SQLite, cho phép quản trị viên điều chỉnh trên giao diện web mà không cần khởi động lại server hay sửa file YAML:

1. **Các Khóa Cấu Hình Động**:
   - `start_time`: Giờ mở cổng FFA hàng ngày (định dạng `HH:MM`, ví dụ `19:00`).
   - `end_time`: Giờ đóng cổng FFA hàng ngày (định dạng `HH:MM`, ví dụ `21:00`).
   - `ffa_mode`: Chế độ mở cổng:
     - `"auto"`: Mở/đóng tự động theo khung giờ giữa `start_time` và `end_time`.
     - `"true"`: Luôn mở cổng bất kể giờ giấc (Override Open).
     - `"false"`: Luôn đóng cổng (Override Closed).
   - `elo_multiplier`: Hệ số nhân Elo thưởng hàng ngày (giá trị từ 1.0 đến 3.0).
   - `current_day`: Ngày thi đấu hiện tại (1 đến n).
2. **Hàm Đánh Giá Trạng Thái Cổng (`is_ffa_portal_open`)**:
   - Nhập tham số: `config`, `current_time_str`, `db_settings`.
   - Xử lý linh hoạt cả khung giờ trong ngày (`19:00` đến `21:00`) lẫn khung giờ xuyên đêm (`22:00` đến `02:00`).

---

## 13. Thiết Kế Giao Diện Minimalist Charcoal & Hệ Thống CSS Tokens
Giao diện web được thiết kế theo phong cách Minimalist Slate/Charcoal dành cho kỹ sư và nhà phát triển, loại bỏ toàn bộ màu neon và hiệu ứng gradient trang trí không cần thiết:

1. **Design Tokens (`web/static/css/style.css`)**:
   - `--bg-main: #0d1117`: Màu nền chính tối giản.
   - `--bg-surface: #161b22`: Màu nền thẻ card, bảng, hộp chứa dữ liệu.
   - `--border-subtle: #30363d`: Đường viền tinh tế 1px độ tương phản cao.
   - `--text-primary: #f0f6fc`: Chữ chính trắng sáng dễ đọc.
   - `--text-muted: #8b949e`: Chữ phụ xám trung tính.
2. **Visualizer Bàn Cờ 9x9 Chuyên Nghiệp**:
   - Thiết kế ô cờ phẳng, nét viền rõ ràng.
   - Thanh điều khiển transport bar hiện đại với nút Play/Pause/Slider tinh gọn.
   - Hiển thị tọa độ a1 - i9 trực quan trên mép bàn cờ.

---

## 14. Hệ Thống Phân Tầng Tài Liệu & Nguyên Tắc Đồng Bộ Tuyệt Đối

Tài liệu dự án được tổ chức theo hệ thống phân tầng nghiêm ngặt, giữ giọng văn học thuật, chuyên nghiệp và không chứa biểu tượng trang trí (icons/emojis):

```text
+------------------------------------------------------------------------+
|                        README.md (Tầng Tiếp Nhận)                      |
|     Entrypoint duy nhất cho người mới, Landing Page, Navigation Index  |
+-----------------------------------┬------------------------------------+
                                    | trỏ trực tiếp đến
+-----------------------------------v------------------------------------+
|                    docs/CONTEXT_RESUME.md (Tầng SSOT)                  |
|       Nguồn Chân Lý Duy Nhất Tối Cao — Quy định luật game, API, CSDL,  |
|         5 Boss Bots, Dynamic Schedule, vai trò 4 thành viên và quy tắc |
+──────────┬────────────────────────┬───────────────────────┬────────────+
           |                        |                       |
           v                        v                       v
+──────────────────────+ +──────────────────────+ +──────────────────────+
| docs/ARCHITECTURE.md | |  docs/BOT_GUIDE.md   | | docs/ADMIN_GUIDE.md  |
|  (Đặc tả kỹ thuật)   | |  (Cẩm nang thí sinh) | | (Cẩm nang vận hành)  |
+──────────────────────+ +──────────────────────+ +──────────────────────+
           |                        |                       |
           +────────────────────────┼───────────────────────+
                                    |
+───────────────────────────────────v------------------------------------+
|                    TASKS.md (Tầng Quản Trị Nhóm)                       |
|    Bảng theo dõi tiến độ Milestones (0 đến 8) & phân chia trách nhiệm  |
|           (Dành cho con người, giảng viên chấm điểm & nghiệm thu)      |
+───────────────────────────────────┬────────────────────────────────----+
                                    | ánh xạ chi tiết sang
+───────────────────────────────────v------------------------------------+
|               docs/specs/ & docs/plans/                                |
|       Blueprint kiến trúc & Kế hoạch thực thi TDD chi tiết cho AI/Dev  |
+------------------------------------------------------------------------+
```

### 14.1 Vai Trò Cụ Thể Của Từng Tài Liệu
1. **`README.md` (Entry Point Bắt Buộc)**:
   - **Mục đích**: Trang hạ cánh (Landing Page) cho người mới, hướng dẫn khởi chạy trong 1 lệnh (`python main.py`), bản đồ chỉ mục điều hướng và FAQ.
   - **Quy tắc**: Tuyệt đối không nhồi nhét chi tiết code schema vào `README.md`. Mọi chi tiết kỹ thuật cốt lõi dẫn link về `docs/CONTEXT_RESUME.md`.
2. **`docs/CONTEXT_RESUME.md` (Single Source of Truth - SSOT)**:
   - **Mục đích**: Bộ nhớ ngữ cảnh trung tâm cho toàn bộ nhóm và mọi AI Agent.
   - **Quy tắc**: Đây là tài liệu có thẩm quyền cao nhất. Mọi thay đổi kiến trúc, CSDL, luật game bắt buộc phải cập nhật vào file này đầu tiên.
3. **Bộ tài liệu chuyên biệt (`docs/ARCHITECTURE.md`, `docs/BOT_GUIDE.md`, `docs/ADMIN_GUIDE.md`)**:
   - Tách bạch phục vụ chính xác 3 đối tượng: Kỹ thuật viên/giáo viên chấm điểm, Thí sinh viết bot, và Ban tổ chức giải đấu.
4. **Mối quan hệ giữa `TASKS.md` và `docs/specs/` & `docs/plans/`**:
   - `TASKS.md` là bảng Kanban cấp cao dành cho con người và chấm điểm học phần theo các Milestones từ 0 đến 8.
   - `docs/specs/` và `docs/plans/` là tài liệu kỹ thuật chi tiết dành cho lập trình viên thực hiện TDD.

### 14.2 Nguyên Tắc Đồng Bộ Tuyệt Đối (Continuous Documentation Sync)
- Khi có bất kỳ sự thay đổi nào về: API (`get_move`, endpoint REST), CSDL (`server/models.py`), luật cờ, boss mới, hoặc quy trình triển khai:
  1. Cập nhật **ngay lập tức** vào `docs/CONTEXT_RESUME.md` (SSOT).
  2. Cập nhật tài liệu chuyên biệt tương ứng (`ARCHITECTURE.md`, `BOT_GUIDE.md`, hoặc `ADMIN_GUIDE.md`).
  3. Cập nhật trạng thái nghiệm thu trong `TASKS.md`.
  4. Đảm bảo `README.md` giữ vững vai trò là bản đồ chỉ mục điều hướng chính xác.

---

## 15. Quy Trình Vận Hành Nhà Máy Tự Động (Autonomous Factory Pipeline)

Hệ thống thiết lập cơ chế vận hành như một nhà máy kỹ thuật phần mềm tự động (Autonomous Engineering Factory), tự động thực hiện chu trình bảo trì, kiểm thử và nâng cấp mà không cần sự can thiệp thủ công của người dùng:

1. **Nguyên Tắc Bất Biến Vận Hành Tự Động (Zero-Human-Intervention Invariant)**:
   - Các chu trình bảo trì và nâng cấp tự động diễn ra theo lịch trình định sẵn (03:00 AM, 05:00 AM, 07:00 AM).
   - AI Agent được trao toàn quyền tự động phát hiện nợ kỹ thuật (technical debt), lỗ hổng kiểm thử, tối ưu hóa hiệu năng, tự động lập kế hoạch, triển khai TDD trên Git Worktree, tự review và merge vào `main`.
2. **Lịch Trình Vận Hành 3 Giai Đoạn (Khung Giờ 3 - 5 - 7)**:
   - **03:00 AM (Khám Phá & Nâng Cấp)**: Kiểm tra sức khỏe hệ thống (`pytest -q`), brainstorm ý tưởng nâng cấp qua 5 danh mục (Hiệu năng, Bảo mật, Trải nghiệm, Chất lượng mã nguồn, Tính năng), chọn giải pháp tác động cao nhất / rủi ro thấp nhất, cô lập trong worktree, triển khai TDD, tự kiểm tra và merge.
   - **05:00 AM (Kiểm Thử Sâu & Đấu Trường Boss Benchmark)**: Thu hồi nhánh dang dở nếu có, chạy mô phỏng đối đầu 10 trận Boss Arena (`scripts/independent_boss_arena_simulation.py`), đánh giá hành vi chiến thuật, nâng cấp thuật toán và phòng thủ bảo mật sandbox, merge vào `main`.
   - **07:00 AM (Tổng Hợp, Dọn Dẹp & Lập Kế Hoạch Tiếp Theo)**: Dọn dẹp các worktree và nhánh tạm, chạy toàn diện test suite hồi quy, kiểm toán tính toàn vẹn tài liệu theo luật SSOT, thực hiện nâng cấp chất lượng mã nguồn (QoL), và tổng hợp báo cáo ngày tại `scratch/maintenance-log-<YYYY-MM-DD>.md`.

---

## 16. Hệ Thống Trực Quan Hóa Lịch Sử Rating & Quỹ Đạo Elo (Rating Trajectory Visualizer)

Nhằm nâng cao động lực thi đấu và tinh thần cạnh tranh trong giải đấu Battlecode RPS 9x9, hệ thống cung cấp công cụ trực quan hóa quỹ đạo Elo tương tác:

1. **Kiến Trúc Tái Thiết Lập Dữ Liệu (`server/rating_history.py`)**:
   - Tái thiết lập các mốc điểm rating trong quá khứ trực tiếp từ các thực thể `Match` đã hoàn thành (`player1_id`, `player2_id`, `p1_elo_after`, `p2_elo_after`, `created_at`) sắp xếp theo thứ tự thời gian (`created_at ASC`), loại bỏ hoàn toàn việc lưu trữ trùng lặp dữ liệu.
   - Hàm `get_user_rating_history(user_id, db, limit=50)`: Trích xuất lịch sử rating của một người chơi cụ thể. Với người chơi chưa thi đấu ván nào (0 matches), hệ thống tự động trả về mốc xuất phát chuẩn (`match_id: 0`, `elo: 1200`, `delta: 0`).
   - Hàm `get_top_teams_rating_history(db, top=5, limit=30)`: Lấy dữ liệu quỹ đạo của Top N đội dẫn đầu trên bảng xếp hạng (tham số `top` được kẹp an toàn trong khoảng [1, 10], `limit` trong khoảng [5, 100]). Mỗi đội được gán một mã màu phân biệt từ bảng màu tối ưu:
     - Hạng 1: Cyan/Teal `#2dd4bf`
     - Hạng 2: Sky Blue `#38bdf8`
     - Hạng 3: Amber `#fbbf24`
     - Hạng 4: Purple `#c084fc`
     - Hạng 5: Rose `#f43f5e`

2. **REST API Endpoints**:
   - `GET /api/leaderboard/rating-history`: Nhận tham số `top: int = 5`, `limit: int = 30`. Trả về JSON chứa danh sách người chơi, thông tin `current_elo`, mã màu nhận diện `color`, và chuỗi các điểm mốc `points` (`match_id`, `created_at`, `elo`, `delta`, `opponent`).
   - `GET /api/users/{user_id}/rating-history`: Nhận tham số `limit: int = 50`. Trả về dữ liệu chi tiết người chơi, điểm hiện tại, điểm cao nhất (peak Elo), điểm thấp nhất (lowest Elo), số trận, và chuỗi lịch sử thi đấu; trả về HTTP 404 sạch khi `user_id` không tồn tại.

3. **Engine Biểu Đồ Vector Thuần (`web/static/js/rating_chart.js` - `RatingChart`)**:
   - Thiết kế theo triết lý Zero-Node.js / Zero-npm bằng Pure SVG và Vanilla JavaScript.
   - Lớp đối tượng `RatingChart` tự động tính toán hệ tọa độ co giãn linh hoạt: trục Y co giãn giữa `min_elo - 50` và `max_elo + 50`, vẽ đường lưới ngang (gridlines) tại các mốc bội số 100 điểm Elo.
   - Vẽ đường đa giác mượt mà `<polyline>` với độ dày 2px và phát sáng tinh tế, cùng các điểm tròn `<circle>` tại từng cột mốc trận đấu.
   - Tích hợp khung thông tin hover tương tác `#chart-tooltip` hiển thị đầy đủ: tên đấu thủ, mã trận, điểm Elo, biến động (+/- delta), đối thủ, và thời gian.
   - Bảng chú giải (legend) tương tác: click hoặc hover vào huy hiệu đội để làm nổi bật đường quỹ đạo tương ứng và làm mờ các đường còn lại.
   - Màn hình thông báo nhắc nhở thân thiện: Khi chưa có đủ 2 trận đấu, hiển thị thông báo hướng dẫn người chơi tham gia thi đấu thêm để biểu đồ xuất hiện.
   - Tương thích hoàn toàn với hệ thống CSS Design Tokens (Slate/Charcoal) của nền tảng.

---

## 17. Hệ Thống Biến Thể Luật Chơi & Đấu Trường Đảo Chiều Ngũ Hành (Tournament Rule Variants & Inverted Combat Cycle)

Nhằm đánh giá năng lực thích ứng thuật toán thực chiến của các đội thi trong các phiên bảo vệ trực tiếp (offline defense) hoặc các vòng thi đấu đặc biệt, hệ thống cung cấp cơ chế hỗ trợ Biến Thể Luật Chơi Động (Dynamic Rule Variants).

1. **Chu Trình Tác Chiến Đảo Chiều Ngũ Hành (Inverted Combat Cycle - `inverted_rps`)**:
   - Quy tắc chuẩn (`standard`): Búa thắng Kéo, Kéo thắng Bao, Bao thắng Búa ($R > S > P > R$).
   - Quy tắc đảo chiều (`inverted_rps`): Kéo thắng Búa, Búa thắng Bao, Bao thắng Kéo ($S > R > P > S$).
   - Quy tắc di chuyển cờ và điều kiện thắng cuộc (chạm đích hàng 9/hàng 1 hoặc tiêu diệt toàn bộ quân đối phương) được giữ nguyên, đảm bảo tính nhất quán của mô hình 9x9.
   - Các hằng số định danh biến thể trong `engine/game.py`: `RULE_VARIANT_STANDARD = "standard"`, `RULE_VARIANT_INVERTED_RPS = "inverted_rps"`, và danh sách hợp lệ `SUPPORTED_RULE_VARIANTS = ["standard", "inverted_rps"]`.
   - Hàm `beats(a, b, variant=RULE_VARIANT_STANDARD)` và các phương thức `is_valid_move`, `make_move`, `generate_legal_moves` trong `engine/game.py` nhận tham số `variant` để kiểm tra tính hợp lệ của nước đi ăn quân theo đúng chu trình tác chiến.
   - Lớp đối tượng `Game(variant=...)` hỗ trợ phương thức `clone()` bảo toàn biến thể và xuất siêu dữ liệu `rule_variant` trong lịch sử trận đấu (`export_history`).

2. **Lưu Trữ & Khởi Tạo Trận Đấu (`server/models.py`, `server/queue.py`)**:
   - Trường dữ liệu `rule_variant` (kiểu chuỗi ký tự, mặc định `"standard"`, không rỗng) được bổ sung vào mô hình bảng CSDL `TournamentSetting` và `Match`.
   - Hàng đợi bất đồng bộ (`server/queue.py`): Khi thực thi trận đấu, hệ thống truy xuất giá trị `rule_variant` từ cài đặt giải đấu hiện hành `TournamentSetting` (hoặc từ chính thực thể `Match.rule_variant` nếu đã được chỉ định trước) và chuyển giao qua `GameRunner.play_match(..., variant=...)`. Sau khi trận đấu kết thúc, giá trị biến thể được lưu vết vĩnh viễn trên bản ghi `Match`.
   - Endpoint tạo trận đấu thách đấu `POST /api/matches/challenge` (`server/routes/matches.py`) tự động sao chép cấu hình `rule_variant` đang hoạt động của giải đấu sang trận đấu mới.

3. **Quản Trị Giải Đấu & Kiểm Thử Thí Sinh (Admin & Competitor Interfaces)**:
   - **Bảng Điều Khiển Quản Trị (`/admin`, `/api/admin/settings`)**: Quản trị viên có thể chuyển đổi biến thể giải đấu theo thời gian thực thông qua menu chọn (dropdown) trên giao diện quản trị mà không cần dừng máy chủ. Schema `TournamentSettingUpdate` thực hiện xác thực nghiêm ngặt để từ chối các mã biến thể không hợp lệ (HTTP 422/400).
   - **Bộ Công Cụ Thí Sinh Offline (`starter_kit/local_arena.py`)**: Thí sinh có thể mô phỏng và kiểm thử bot ngoại tuyến độc lập với máy chủ thông qua tham số dòng lệnh `--variant`:
     ```bash
     python starter_kit/local_arena.py my_bot.py starter_kit/heuristic_bot.py --variant inverted_rps --rounds 10
     ```
   - **Trình Trực Quan Hóa Replay (`web/templates/replay.html`, `web/static/js/visualizer.js`)**: Khi xem lại các trận đấu thuộc biến thể `inverted_rps`, giao diện hiển thị huy hiệu nhận diện nổi bật "Chế độ: Đảo chiều ngũ hành (Kéo > Búa > Bao)" trên thanh điều hướng phát lại.

## 18. WAN Deployment & HTTPS Tunnel Configuration

Hệ thống hỗ trợ triển khai thử nghiệm qua WAN bằng mô hình HTTPS tunnel, phục vụ demo khi người dùng không cùng mạng LAN.

1. Biến môi trường triển khai:
   - ALLOWED_ORIGINS: Danh sách origin được phép truy cập CORS, phân tách bằng dấu phẩy.
   - COOKIE_SECURE: Mặc định để trống (auto) - cookie phiên tự bật cờ Secure khi request đến qua HTTPS (kể cả qua tunnel), tắt khi chạy HTTP LAN. Đặt true/false để ép buộc.
   - ADMIN_USERNAME và ADMIN_PASSWORD: Cấu hình tài khoản quản trị được seed khi khởi động.

2. Cấu hình mặc định local:
   - ALLOWED_ORIGINS mặc định gồm http://localhost:8000 và http://127.0.0.1:8000.
   - COOKIE_SECURE mặc định là auto (theo scheme của request) để đăng nhập hoạt động cả trên HTTP local lẫn HTTPS tunnel.

3. Cấu hình WAN demo:
   - Khi dùng Cloudflare Tunnel hoặc HTTPS public endpoint, đặt ALLOWED_ORIGINS trùng chính xác với URL HTTPS public.
   - Không cần đặt COOKIE_SECURE: chế độ auto tự nhận HTTPS nhờ uvicorn proxy headers (tin cậy proxy trong FORWARDED_ALLOW_IPS, mặc định 127.0.0.1).
   - Không sử dụng mật khẩu mặc định admin123 khi public hệ thống ra Internet.

4. Quy tắc chạy kiểm thử:
   - Trước khi chạy pytest, phải xóa các biến môi trường WAN như ADMIN_PASSWORD, ADMIN_USERNAME, COOKIE_SECURE và ALLOWED_ORIGINS.
   - Nếu ADMIN_PASSWORD còn giữ giá trị demo WAN, test suite có thể fail vì các test mặc định dùng admin/admin123.

## 19. Kiến Trúc Đa Trò Chơi (Multi-Game Registry)

1. **Danh mục game (`engine/games/__init__.py`)**:
   - `GAMES`: metadata hiển thị cho mọi game, khóa bằng slug ổn định: `connect4` (Connect Four 6x7, độ khó 1), `caro` (Caro/Gomoku 15x15, độ khó 2), `rps9x9` (Cờ Oẳn Tù Tì 9x9, độ khó 3, game mặc định `DEFAULT_GAME`).
   - Hàm tiện ích: `SUPPORTED_GAMES`, `list_games()` (sắp từ dễ đến khó), `normalize_game_type()`, `is_grid_game()`, `create_grid_game()`.
   - Engine RPS gốc `engine/game.py` giữ nguyên, chỉ được đăng ký vào danh mục.
2. **Engine game lưới (`engine/games/grid.py`)**:
   - Lớp `GridGame` dùng chung: bàn cờ ma trận số nguyên (0 trống, 1/2 quân người chơi), Player 1 đi trước, thắng khi có `win_length` quân thẳng hàng (ngang/dọc/chéo), bàn đầy thì hòa (`win_reason`: `line` hoặc `board_full`).
   - `Connect4Game`: 6 hàng x 7 cột, `gravity = True`, nước đi là `int` (chỉ số cột), hàng 0 là hàng trên cùng.
   - `CaroGame`: 15 x 15, nước đi là `(row, col)`, 5 quân trở lên thẳng hàng là thắng.
3. **Bot interface thống nhất**: mọi game dùng chung `get_move(board, my_player, history)`. Với game lưới, `history` là danh sách `{'turn', 'player', 'move', 'cell'}`.
4. **Runner (`engine/runner.py`)**: `run_match(..., game_type="rps9x9")`. Game lưới chạy qua `_run_grid_match` với cùng `BotProcess` cô lập, timeout và luật xử thua (`timeout`, `error`, `invalid_move`). Replay JSON có thêm `game_type`, `rows`, `cols`, `winning_line`; replay RPS cũng có `game_type: "rps9x9"`.
5. **CSDL**: cột `game_type` (String(32), mặc định `"rps9x9"`) trên bảng `Bot` và `Match`. `init_db()` tự `ALTER TABLE` thêm cột cho các file `app.db` cũ (`ADDED_COLUMNS` trong `server/database.py`).
6. **Game đang thi đấu**: khóa `game_type` trong `TournamentSetting`, admin chọn trên `/admin` (API `POST /api/admin/settings` với `game_type`). `server/games.py` cung cấp `get_active_game()` và `get_active_bot(db, user_id, game_type)`.
   - Mỗi người dùng có tối đa 1 bot kích hoạt cho TỪNG game; upload (`POST /api/bots/upload`, form field `game_type`, mặc định game đang thi đấu) và activate chỉ tắt bot cùng game.
   - Thách đấu FFA và Bracket dùng bot kích hoạt của game đang thi đấu; `Match.game_type` lưu game của trận.
   - Lưu ý: Elo vẫn là một chỉ số chung trên `User`. Khi đổi game giữa các buổi, ban tổ chức nên coi mỗi buổi là một mùa giải riêng.
7. **Starter kit**: `connect4_template.py`, `connect4_bot.py`, `caro_template.py`, `caro_bot.py`, đối thủ chuẩn `starter_kit/opponents/`. `local_arena.py` có cờ `--game {rps9x9,connect4,caro}`.
8. **Boss Arena**: 5 boss server-side vẫn chỉ dành cho RPS 9x9.

## 20. Website Công Khai & Các Trang Web (Public Website)

| Route | Template | Mục đích |
| :--- | :--- | :--- |
| `/` | `home.html` | Trang chủ: giới thiệu, 4 bước cho người mới, thẻ 3 game, trạng thái cổng, địa chỉ chia sẻ (LAN/WAN), top 5 |
| `/leaderboard` | `index.html` | Bảng xếp hạng Elo + thách đấu FFA (trước đây nằm ở `/`) |
| `/games`, `/games/{slug}` | `games.html`, `game_detail.html` | Danh sách game; luật, cấu trúc bàn cờ, code mẫu đọc trực tiếp từ `starter_kit/`, lệnh test/chấm |
| `/play/{slug}` | `play.html` | Chơi với máy ngay trong trình duyệt (`web/static/js/games.js` + `board_view.js`, chạy hoàn toàn phía client) |
| `/guide` | `guide.html` | Hướng dẫn 6 bước cho sinh viên năm nhất, lỗi thường gặp, FAQ |
| `/guide/organizer` | `organizer.html` | Cẩm nang ban tổ chức: LAN offline, WAN, điều hành, chấm điểm, kịch bản 120 phút |
| `/grade` | `grade.html` | Tự chấm điểm bot trên web |
| `/replay/{id}` | `replay.html` hoặc `replay_grid.html` | Replay RPS 9x9 hoặc replay game lưới (tự chọn theo `Match.game_type`) |
| `/download/starter-kit.zip` | - | Bộ công cụ offline (starter_kit, engine, grader, server/bosses, BOT_GUIDE) |

- Giao diện: `web/static/css/site.css` (lớp site, nạp sau `style.css` và `arena-light.css`), navbar có menu thu gọn cho mobile, không phụ thuộc CDN hay font ngoài (chạy được trong LAN khép kín).
- Biến Jinja toàn cục: `games_list`, `games_map`.

## 21. Chấm Điểm Tự Động (Auto-Grader)

1. **Lõi (`engine/grader.py`)**: `grade_bot(bot_path, game_type, games_per_opponent=4)` kiểm tra AST sandbox (không qua = 0 điểm), cho bot đấu với thang đối thủ chuẩn `GRADING_LADDERS` (đổi lượt đi trước mỗi ván; thắng 1, hòa 0.5), điểm = `10 * sum(trọng số * tỉ lệ điểm) / sum(trọng số)`, xếp loại theo `GRADE_BANDS` (Xuất sắc >= 9, Giỏi >= 7, Khá >= 5, Trung bình >= 3).
   - `connect4` / `caro`: Random (Lv1, trọng số 4), Heuristic (Lv2, trọng số 6).
   - `rps9x9`: Novice (3), Heuristic (3), Rusher (4).
2. **CLI offline (`starter_kit/grade.py`)**: `python starter_kit/grade.py <bot.py | thư_mục> --game connect4 [--games N] [--csv diem.csv]` - chấm một bot hoặc cả lớp, xuất CSV.
3. **API web (`server/routes/grade.py`)**: `POST /api/grade` (đăng nhập; form `game_type`, `file` tùy chọn - nếu không có file thì chấm bot đang kích hoạt; file upload chỉ dùng để chấm, không thay bot thi đấu) trả về `job_id` (HTTP 202); `GET /api/grade/{job_id}` trả tiến trình và báo cáo (chỉ chủ job xem được). Tối đa 2 job chấm chạy đồng thời (`MAX_CONCURRENT_GRADINGS`).
4. **Xuất bảng xếp hạng**: `GET /api/leaderboard/export.csv` (UTF-8 BOM cho Excel, loại tài khoản admin và boss).

## 22. Tối Ưu Truy Cập WAN

1. `python main.py --tunnel`: khởi động Cloudflare quick tunnel (`cloudflared tunnel --url http://localhost:<port>`), đọc URL `https://*.trycloudflare.com` (`parse_tunnel_url`), đặt biến `PUBLIC_URL` và in dòng `Public WAN URL` trên banner. Thiếu `cloudflared` thì cảnh báo và tiếp tục chạy LAN.
2. `python main.py --public-url https://...` (hoặc biến `PUBLIC_URL`): dùng cho VPS/reverse proxy riêng.
3. `server/network.py`: `get_lan_ip()` (chuyển từ `main.py`, `main` vẫn import lại), `get_public_url(request)` (ưu tiên `PUBLIC_URL`, nếu truy cập bằng localhost thì thay bằng IP LAN), `should_use_secure_cookie(request)` (COOKIE_SECURE auto/true/false).
4. `GZipMiddleware` (minimum_size 1024) nén HTML/JSON/replay; trận đấu chạy hoàn toàn phía server nên độ trễ mạng không ảnh hưởng giới hạn 1 giây/nước; trang replay game lưới tự thử lại khi trận còn đang chạy.

## 23. An Toàn Dữ Liệu Khi Chạy Test

- Một số test xóa `app.db`, `bots/`, `replays/` trong thư mục làm việc. `tests/conftest.py` (fixture `preserve_dev_data`, scope session) di chuyển các dữ liệu này sang thư mục tạm trước khi chạy và khôi phục sau khi xong, nên chạy `pytest` không còn làm mất dữ liệu dev. Hãy tắt server dev (đang mở `app.db`) trước khi chạy test trên Windows.
- Với Starlette 1.x, `fastapi.testclient` cần gói `httpx2` (`pip install httpx2`) để chạy test suite.

- 2026-10-18: Applied the approved clubhouse UI from `.worktrees/midterm-review` to the original checkout at the user request. Includes local SVG pieces, club-room home, compact interior pages and admin-managed public catalog (RPS only by default). Previous affected source files backed up under `local_backups/`. Local databases and uploaded bots were not copied. No GitHub push.
