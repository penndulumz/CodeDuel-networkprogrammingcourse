# 🏆 Battlecode RPS Platform — Nền Tảng Thi Đấu Thuật Toán Cờ Oẳn Tù Tì 9×9

> **Hệ thống thi đấu đối kháng bot tự động (Battlecode-style)** dành cho sinh viên. Sinh viên lập trình chiến thuật bot bằng Python để điều khiển các quân cờ Oẳn Tù Tì trên bàn cờ 9×9, tham gia đấu rank FFA hàng ngày và tranh tài tại giải đấu loại trực tiếp (Bracket) ngày chung kết.

---

## ⚡ 1. Khởi Chạy Nhanh (Quickstart Trong 1 Lệnh)

Hệ thống được thiết kế **Zero-Node.js & Local-First** — chỉ cần môi trường Python:

### Bước 1: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy máy chủ
```bash
python main.py
```
- 🌐 **Giao diện Web**: [http://localhost:8000](http://localhost:8000)
- 📚 **Tài liệu API Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🔑 **Tài khoản Quản Trị (Admin) mặc định**:
  - Tên đăng nhập: `admin`
  - Mật khẩu: `admin123`

*(Máy chủ tự động khởi tạo cơ sở dữ liệu SQLite `app.db` và nạp sẵn 2 bot mẫu vào hệ thống).*

---

## 📂 2. Cấu Trúc Thư Mục Hệ Thống (Folder Structure)

```text
Battlecode-clone0810/
├── main.py                      # Entrypoint 1 lệnh khởi động toàn bộ server & DB
├── requirements.txt             # Thư viện Python tối giản (FastAPI, SQLAlchemy, PyYAML...)
├── pytest.ini                   # Cấu hình test tự động
├── TASKS.md                     # Bảng phân chia công việc nhóm 4 người & tiến độ (100% PASS)
├── GEMINI.md                    # File ngữ cảnh tự động cho AI (Antigravity/Gemini)
│
├── config/
│   └── tournament.yaml          # Cấu hình giải đấu (số ngày n, giờ mở cổng, hệ số x, max turn)
│
├── engine/                      # Core Game Logic (Python thuần, chạy độc lập)
│   ├── game.py                  # Luật game cờ Oẳn Tù Tì 9x9, bàn cờ, kiểm tra thắng thua
│   ├── runner.py                # Runner chạy ván đấu giữa 2 bot (timeout 1.0s, bắt lỗi, IPC)
│   └── sandbox.py               # Bộ lọc AST bảo mật (chặn triệt để os, sys, socket, eval, open)
│
├── server/                      # FastAPI Backend & Cơ sở dữ liệu
│   ├── main.py                  # Khởi tạo FastAPI app, định tuyến API & web templates
│   ├── database.py              # SQLite engine với chế độ WAL chống khóa file
│   ├── models.py                # Bảng CSDL: User, Bot, Match, TournamentSetting, BracketMatch
│   ├── queue.py                 # Hàng đợi trận đấu bất đồng bộ (Background worker)
│   ├── tournament.py            # Thuật toán tính Elo (hệ số x), bốc thăm giải đấu Bracket
│   ├── tournament_config.py     # Bộ nạp cấu hình giải đấu từ file YAML
│   └── routes/                  # REST API Endpoints
│       ├── auth.py              # Đăng ký, đăng nhập (Session cookie / Header token)
│       ├── bots.py              # Nộp code bot .py (quét sandbox trước khi lưu)
│       ├── matches.py           # Thách đấu FFA, lấy lịch sử trận, lấy file replay JSON
│       ├── leaderboard.py       # Bảng xếp hạng Elo, hồ sơ người chơi
│       └── admin.py             # Điều khiển giải, bật/tắt cổng FFA, tạo Bracket chung kết
│
├── web/                         # Giao diện Web (HTML5/CSS3/Vanilla JS - Zero npm)
│   ├── static/
│   │   ├── css/style.css        # Giao diện Dark mode mượt mà, bàn cờ 9x9, thẻ quân cờ
│   │   └── js/visualizer.js     # Trình chiếu replay trận đấu tương tác (Play, Pause, Step, Slider)
│   └── templates/               # Giao diện Jinja2
│       ├── base.html            # Layout chung (Navbar, Header)
│       ├── index.html           # Trang chủ & Bảng xếp hạng Elo (Nút "Thách đấu")
│       ├── login.html           # Đăng nhập
│       ├── register.html        # Đăng ký tài khoản
│       ├── profile.html         # Hồ sơ cá nhân, nộp code bot & lịch sử thi đấu
│       ├── replay.html          # Sân đấu trực quan xem lại diễn biến từng ván cờ
│       ├── admin.html           # Trang quản trị giải đấu (Bật/tắt cổng, đổi hệ số x)
│       └── bracket.html         # Sơ đồ cây giải đấu loại trực tiếp ngày chung kết
│
├── starter_kit/                 # Gói tài liệu & công cụ phát cho thí sinh tải về máy
│   ├── bot_template.py          # Bot mẫu cơ bản (RandomBot)
│   ├── heuristic_bot.py         # Bot chiến thuật thông minh (HeuristicBot)
│   ├── local_arena.py           # Công cụ CLI để thí sinh tự chạy đấu thử 2 bot trên máy nhà
│   └── README.md                # Hướng dẫn chi tiết dành cho thí sinh
│
├── docs/                        # Tài liệu đặc tả kỹ thuật dự án
│   ├── CONTEXT_RESUME.md        # Bộ nhớ ngữ cảnh trung tâm cho Đa-LLM & Master Prompt
│   └── superpowers/             # Bản thiết kế (Specs) & kế hoạch thực thi (Plans)
│
└── tests/                       # Bộ kiểm thử tự động (167 test cases)
    ├── test_game.py             # Kiểm tra luật cờ 9x9, ăn quân, ô đích, diệt sạch quân
    ├── test_sandbox.py          # Kiểm tra bắt mã độc AST (74 kịch bản tấn công)
    ├── test_starter_kit.py      # Kiểm tra starter kit và CLI local arena
    ├── test_runner.py           # Kiểm tra timeout 1s, crash, sinh file replay
    ├── test_database.py         # Kiểm tra CSDL SQLite và cấu hình giải
    ├── test_tournament.py       # Kiểm tra công thức Elo, hệ số x, bốc thăm Bracket
    ├── test_api.py              # Kiểm tra toàn bộ REST API
    ├── test_web.py              # Kiểm tra hiển thị giao diện web
    └── test_e2e.py              # Kiểm tra toàn vẹn luồng người dùng từ A-Z
```

---

## 🎮 3. Luật Chơi Cờ Oẳn Tù Tì 9×9

1. **Bàn cờ & Tọa độ**: Kích thước 9×9 ô (`a1` đến `i9`).
2. **Quân cờ & Tương khắc**:
   - `R` (Đấm ✊), `P` (Lá ✋), `S` (Kéo ✌).
   - **Quy tắc**: `Đấm > Kéo`, `Kéo > Lá`, `Lá > Đấm`.
   - Cùng loại quân sẽ chặn nhau không thể đi vào. Thua Oẳn Tù Tì không được đi vào ô đó.
3. **Bố trí xuất phát**:
   - **Player 1 (Đỏ - Đi trước)**: Hàng 1 (`rank 1`): `[R, R, R, P, P, P, S, S, S]`. Đích cần đến: `i9`.
   - **Player 2 (Xanh - Đi sau)**: Hàng 9 (`rank 9`): `[S, S, S, P, P, P, R, R, R]`. Đích cần đến: `a1`.
4. **Cách di chuyển**: Mỗi quân đi 1 ô theo 8 hướng (như quân Vua trong cờ vua).
5. **Điều kiện thắng cuộc**:
   - 🚩 **Chạm đích (Goal)**: Đưa bất kỳ quân nào vào ô đích đối phương (`i9` cho P1, `a1` cho P2).
   - 💥 **Diệt sạch (Wipeout)**: Ăn hết cả 3 quân cùng 1 loại (toàn bộ Đấm, hoặc toàn bộ Lá, hoặc toàn bộ Kéo) của đối phương.
   - ⏱️ **Xử thua kỹ thuật**: Bot vi phạm thời gian (> 1.0 giây/turn) hoặc bị lỗi ngoại lệ (crash).
   - ⌛ **Hết lượt (200 Turns)**: Bên nào còn nhiều tổng số quân hơn sẽ thắng; bằng nhau tính Hòa.

---

## 🤖 4. Hướng Dẫn Dành Cho Thí Sinh (Viết & Nộp Bot)

### Viết Bot Python
Thí sinh tạo một file Python (ví dụ `my_bot.py`) và cài đặt hàm bắt buộc:

```python
def get_move(board, my_player, history):
    """
    Args:
        board: Ma trận 9x9, board[row][col] là None hoặc {'type': 'R'|'P'|'S', 'player': 1|2}
        my_player: 1 (Đỏ, đi trước) hoặc 2 (Xanh, đi sau)
        history: Danh sách nước đi trước đó [{'player': 1, 'from': (0, 3), 'to': (1, 3), 'san': '...'}]

    Returns:
        ((from_row, from_col), (to_row, to_col))
    """
    # Viết chiến thuật của bạn tại đây
    return ((0, 0), (1, 1))
```

### Chạy Thử Trên Máy Cá Nhân (Local Arena)
Thí sinh không cần kết nối server vẫn có thể test thử bot bằng script có sẵn trong `starter_kit/`:
```bash
python starter_kit/local_arena.py my_bot.py starter_kit/heuristic_bot.py --rounds 5
```

### Nộp Bot Lên Server
1. Đăng ký tài khoản trên web [http://localhost:8000/register](http://localhost:8000/register).
2. Vào mục **Hồ Sơ (Profile)**, kéo thả file `.py` vào form nộp code.
3. Server tự động quét mã độc bằng AST. Nếu hợp lệ, bot sẽ được kích hoạt ngay lập tức. Mã nguồn của bạn được bảo mật tuyệt đối trên server, không đối thủ nào có thể xem được.

---

## 🏆 5. Thể Thức Giải Đấu & Bảng Xếp Hạng

### Vòng Bảng FFA (Ngày 1 đến Ngày $n$)
- Cổng thi đấu mở theo khung giờ cấu hình (mặc định 19:00 - 21:00 hàng ngày).
- Trong khung giờ này, thí sinh vào **Bảng Xếp Hạng** và bấm nút **"Thách đấu"** bất kỳ đối thủ nào.
- Trận đấu tự động chạy ngầm trên server và cập nhật điểm Elo ngay sau khi kết thúc.
- **Hệ số ngẫu nhiên $x$ theo ngày**: Mỗi ngày có hệ số $x \in [1.0, 3.0]$. Điểm Elo nhận/mất sẽ nhân với $x$:
  $$\Delta\text{Elo} = \text{round}(x \times 32 \times (S - E))$$

### Chung Kết Loại Trực Tiếp (Ngày $n+1$: Bracket Playoff)
- Đóng cổng nộp code và thách đấu FFA.
- Top 8 (hoặc Top 16) người có điểm Elo cao nhất được đưa vào sơ đồ thi đấu loại trực tiếp (BO3 đổi lượt).
- Điểm tổng kết toàn giải kết hợp giữa Elo tích lũy và thành tích Bracket.

---

## 🛠️ 6. Kiểm Thử Hệ Thống (Automated Testing)

Chạy toàn bộ 167 unit, integration và end-to-end test cases:
```bash
pytest -v
```
Toàn bộ test đều chạy tự động và độc lập, không yêu cầu cài đặt thêm bất kỳ service bên ngoài nào.
