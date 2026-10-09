# 🏆 Battlecode RPS Platform — Nền Tảng Thi Đấu Thuật Toán Cờ Oẳn Tù Tì 9×9

> **Hệ thống thi đấu đối kháng bot tự động (Battlecode-style)** dành cho sinh viên. Sinh viên lập trình thuật toán điều khiển quân cờ Oẳn Tù Tì trên bàn cờ 9×9, thi đấu rank FFA hàng ngày và tranh tài tại giải đấu loại trực tiếp (Bracket BO3) ngày chung kết.
>
> ⚠️ **LƯU Ý VỀ SINGLE SOURCE OF TRUTH (SSOT)**:  
> File **[`docs/CONTEXT_RESUME.md`](docs/CONTEXT_RESUME.md)** là **Nguồn Chân Lý Duy Nhất** chi phối toàn bộ kiến trúc hệ thống, luật cờ 9×9, chữ ký hàm bot, cơ sở dữ liệu và workflow của nhóm. Hãy đọc `docs/CONTEXT_RESUME.md` để nắm rõ toàn bộ quy ước cốt lõi!

---

## ⚡ 1. Khởi Chạy Nhanh (Quickstart Trong 1 Lệnh)

Hệ thống được thiết kế **Zero-Node.js & Local-First** — chỉ cần môi trường Python (>= 3.10):

### Bước 1: Cài đặt thư viện
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy máy chủ
```bash
python main.py
```

Console khởi động sẽ hiển thị trực tiếp các địa chỉ truy cập:
- 🌐 **Giao diện Web cục bộ**: [http://localhost:8000](http://localhost:8000)
- 📡 **Địa chỉ Mạng Nội Bộ (LAN)**: `http://<LAN_IP>:8000` *(Chia sẻ cho các máy khác trong cùng Wi-Fi/mạng dây)*
- 🛠️ **Trang Quản Trị Giải Đấu**: [http://localhost:8000/admin](http://localhost:8000/admin) *(Tài khoản mặc định: `admin` / `admin123`)*
- 📚 **Tài liệu API Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🧭 2. Bản Đồ Điều Hướng Tài Liệu (Documentation Directory)

Để tránh lặp lại thông tin và phục vụ chính xác từng đối tượng, tài liệu dự án được phân chia chuyên biệt:

| Đối Tượng | Tài Liệu Hướng Dẫn | Nội Dung Trọng Tâm |
| :--- | :--- | :--- |
| **Tất cả mọi người & AI** | 📄 **[`docs/CONTEXT_RESUME.md`](docs/CONTEXT_RESUME.md)** | **SSOT Cốt Lõi**: Luật game 9×9, bot API, CSDL, phân chia 4 vai trò, luật Continuous Feedback Loop. |
| **Thí sinh & Sinh viên** | 🤖 **[`docs/BOT_GUIDE.md`](docs/BOT_GUIDE.md)** | **Cẩm Nang Viết Bot**: Hệ tọa độ `a1`-`i9`, combat RPS, 2 cách thắng (Goal & Wipeout), test offline với `local_arena.py`. |
| **Ban tổ chức & Quản trị** | 🛠️ **[`docs/ADMIN_GUIDE.md`](docs/ADMIN_GUIDE.md)** | **Vận Hành Giải Đấu**: Single-Admin bảo mật, mở cổng LAN & firewall, đổi hệ số $x$, bốc thăm Playoff BO3. |
| **Kỹ thuật viên & Chấm điểm** | 🏗️ **[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)** | **Đặc Tả Kỹ Thuật**: Kiến trúc 4 tầng, AST sandbox (74 mẫu tấn công), Subprocess IPC timeout 1s, SQLite WAL. |
| **Thành viên nhóm dự án** | 📋 **[`TASKS.md`](TASKS.md)** & **[`GEMINI.md`](GEMINI.md)** | Phân chia tiến độ 4 thành viên, quy ước Git Worktrees cách ly và bảo tồn thư mục gốc. |

---

## 📂 3. Cấu Trúc Thư Mục Dự Án (Folder Structure)

```text
Battlecode-clone0810/
├── main.py                      # Entrypoint khởi chạy server, dò IP mạng LAN & seeder admin
├── requirements.txt             # Thư viện tối giản (FastAPI, SQLAlchemy, PyYAML, pytest)
├── pytest.ini                   # Cấu hình kiểm thử tự động
├── TASKS.md                     # Bảng tiến độ & nghiệm thu của nhóm 4 thành viên
├── GEMINI.md                    # Chỉ dẫn AI tuân thủ SSOT & quy ước Git Worktrees
│
├── config/
│   └── tournament.yaml          # Cấu hình giải (số ngày n, khung giờ mở cổng, hệ số x, max turns)
│
├── engine/                      # Core Game Logic (Python thuần, chạy độc lập)
│   ├── game.py                  # Luật cờ 9×9 Oẳn Tù Tì, ma trận tọa độ, Goal & Wipeout
│   ├── runner.py                # Isolated Subprocess Runner (giám sát timeout 1.0s, bắt crash)
│   └── sandbox.py               # Bộ lọc AST bảo mật (chặn triệt để os, sys, socket, eval, open)
│
├── server/                      # FastAPI Backend & CSDL
│   ├── main.py                  # Ứng dụng FastAPI, mount static & template HTML
│   ├── database.py              # SQLite engine với chế độ WAL chống khóa file
│   ├── models.py                # Bảng CSDL: User, Bot, Match, TournamentSetting, BracketMatch
│   ├── queue.py                 # Hàng đợi trận đấu bất đồng bộ (Background worker)
│   ├── tournament.py            # Công thức tính Elo (hệ số x) & bốc thăm Bracket Playoff
│   └── routes/                  # REST API Endpoints (auth, bots, matches, leaderboard, admin)
│
├── web/                         # Giao diện Web (Zero-Node.js / Zero-npm)
│   ├── static/                  # CSS Dark-mode & visualizer.js tương tác xem replay bàn cờ 9×9
│   └── templates/               # Giao diện Jinja2 (Leaderboard, Profile, Replay, Admin, Bracket)
│
├── starter_kit/                 # Bộ công cụ phát cho thí sinh tải về máy làm việc offline
│   ├── bot_template.py          # Bot mẫu cơ bản
│   ├── heuristic_bot.py         # Bot chiến thuật mẫu thông minh
│   ├── local_arena.py           # CLI giả lập đấu thử 2 bot trực tiếp trên máy nhà
│   └── README.md                # Hướng dẫn nhanh cho thí sinh
│
├── docs/                        # Thư viện tài liệu chuyên biệt
│   ├── CONTEXT_RESUME.md        # Single Source of Truth tối cao
│   ├── ARCHITECTURE.md          # Đặc tả kiến trúc kỹ thuật sâu
│   ├── BOT_GUIDE.md             # Cẩm nang toàn tập cho thí sinh viết bot
│   ├── ADMIN_GUIDE.md           # Cẩm nang vận hành giải đấu & mạng LAN
│   ├── logs/                    # Nhật ký sức khỏe và bảo trì định kỳ tự động
│   └── superpowers/             # Thiết kế kiến trúc (specs) & kế hoạch thực thi (plans)
│
└── tests/                       # Toàn bộ 171 test cases tự động (100% PASS)
```

---

## ❓ 4. Các Câu Hỏi Thường Gặp (Frequently Asked Questions - FAQ)

### Q1: Làm thế nào để các máy tính khác trong phòng thi đấu kết nối vào server?
Máy chủ mặc định lắng nghe trên `0.0.0.0:8000`. Khi khởi động `python main.py`, console sẽ in ra địa chỉ **LAN Network URL** (ví dụ: `http://192.168.1.15:8000`). Mọi máy tính kết nối chung mạng Wi-Fi hoặc mạng dây chỉ cần gõ địa chỉ đó vào trình duyệt là có thể đăng ký tài khoản và nộp bot. Nếu máy khác không vào được, hãy kiểm tra tường lửa theo hướng dẫn tại [`docs/ADMIN_GUIDE.md`](docs/ADMIN_GUIDE.md).

### Q2: Mã nguồn bot của tôi có bị các đối thủ khác xem trộm không?
**Tuyệt đối không.** Toàn bộ mã nguồn bot được lưu trữ kín trên máy chủ trong thư mục riêng tư (`bots/`). Các đối thủ chỉ nhận được file Replay JSON ghi lại nước đi và tọa độ trên bàn cờ, hoàn toàn không thể xem hoặc tải về file `.py` của bạn.

### Q3: Tài khoản Admin được quản lý thế nào? Người khác có tự tạo Admin được không?
Hệ thống tuân thủ nguyên tắc **Single-Admin Invariant**:
- Chỉ có đúng **1 tài khoản Admin duy nhất** trong hệ thống.
- Cấu hình tài khoản admin qua biến môi trường `ADMIN_USERNAME` và `ADMIN_PASSWORD` (mặc định: `admin` / `admin123`).
- API đăng ký sẽ từ chối ngay lập tức mọi nỗ lực đăng ký username `admin` hoặc trùng với `ADMIN_USERNAME`.
- Seeder máy chủ sẽ tự động tước quyền (`is_admin = False`) đối với bất kỳ tài khoản giả mạo nào khác.

### Q4: Tại sao bot của tôi bị xử thua kỹ thuật?
Một bot sẽ bị xử thua ngay lập tức nếu:
1. Chạy quá **1.0 giây** cho 1 lượt tính toán (`win_reason = 'timeout'`).
2. Mã nguồn phát sinh lỗi ngoại lệ hoặc crash (`win_reason = 'error'`).
3. Trả về nước đi không hợp lệ (sai tọa độ hoặc đi quân ngược luật) (`win_reason = 'invalid_move'`).

### Q5: Tôi có thể phát triển và đấu thử bot mà không cần kết nối server không?
**Có.** Bạn chỉ cần tải thư mục [`starter_kit/`](starter_kit/) về máy cá nhân và dùng lệnh:
```bash
python starter_kit/local_arena.py my_bot.py starter_kit/heuristic_bot.py --rounds 10
```
Công cụ này chạy trực tiếp trên máy của bạn, không cần cài đặt server hay kết nối mạng. Xem chi tiết tại [`docs/BOT_GUIDE.md`](docs/BOT_GUIDE.md).

### Q6: Hệ số nhân Elo $x$ hàng ngày hoạt động thế nào?
Trong $n$ ngày vòng bảng, cổng thi đấu mở theo khung giờ cố định (19:00 - 21:00). Mỗi ngày ban tổ chức áp dụng một hệ số ngẫu nhiên $x \in [1.0, 3.0]$. Điểm Elo tăng/giảm sau mỗi trận sẽ nhân với $x$:
$$\Delta\text{Elo} = \text{round}(x \times 32 \times (S - E))$$
Những ngày có hệ số $x$ cao là cơ hội lớn để bứt phá thứ hạng!

---

## 🧪 5. Kiểm Thử Hệ Thống (Automated Testing)

Chạy toàn bộ 171 bài kiểm thử tự động (Engine, Sandbox, Runner, Database, Tournament Elo, REST API, Web UI, LAN Banner, Admin Security và E2E):

```bash
pytest -v
```

Mọi bài kiểm thử đều chạy tự động và độc lập trong vài giây, đảm bảo độ tin cậy tuyệt đối cho hệ thống.
