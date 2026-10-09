# 🛠️ Cẩm Nang Quản Trị Viên: Vận Hành Giải Đấu & Triển Khai Đa Máy (Admin Guide)

> **Dành cho**: Ban tổ chức giải đấu, trọng tài, kỹ thuật viên quản trị hệ thống.  
> **Source of Truth**: [`docs/CONTEXT_RESUME.md`](CONTEXT_RESUME.md)

---

## 1. Cơ Chế Bảo Mật Duy Nhất Một Admin (Single-Admin Security)

Hệ thống được thiết kế theo nguyên tắc **Single-Admin Invariant**:
- Trong toàn bộ hệ thống CSDL, chỉ tồn tại **DUY NHẤT 1 TÀI KHOẢN ADMIN**.
- **Không ai có thể tự tạo tài khoản admin**: Endpoint đăng ký `/api/auth/register` sẽ từ chối ngay lập tức mọi nỗ lực đăng ký username mang tên `admin` hoặc trùng với `ADMIN_USERNAME` (không phân biệt hoa thường).
- **Tự động thanh trừng quyền admin giả mạo**: Mỗi khi máy chủ khởi động hoặc chạy seeder, nếu phát hiện bất kỳ tài khoản nào khác có `is_admin = True`, hệ thống sẽ tự động hạ quyền xuống `is_admin = False`.

### 1.1 Cấu hình thông tin Admin qua Biến Môi Trường
Bạn có thể tùy chỉnh tên đăng nhập và mật khẩu admin trước khi khởi chạy server:

**Trên Windows (PowerShell):**
```powershell
$env:ADMIN_USERNAME = "superadmin"
$env:ADMIN_PASSWORD = "SecretPassword2026!"
python main.py
```

**Trên Linux / macOS:**
```bash
export ADMIN_USERNAME="superadmin"
export ADMIN_PASSWORD="SecretPassword2026!"
python main.py
```

*(Nếu không đặt biến môi trường, tài khoản mặc định sẽ là `admin` / `admin123`).*

---

## 2. Triển Khai Đa Máy Qua Mạng Nội Bộ (Multi-Machine LAN Setup)

Để các thí sinh sử dụng máy tính riêng (cùng mạng Wi-Fi hoặc mạng dây LAN) có thể truy cập vào máy chủ nộp code và thách đấu:

### Bước 1: Khởi động máy chủ
Máy chủ mặc định lắng nghe trên mọi card mạng (`0.0.0.0`):
```bash
python main.py --host 0.0.0.0 --port 8000
```

Console khởi động sẽ tự động dò và in địa chỉ IP mạng nội bộ của bạn:
```text
========================================================================
           BATTLECODE 9x9 ROCK-PAPER-SCISSORS PLATFORM
========================================================================
  Local URL:          http://localhost:8000
  LAN Network URL:    http://192.168.1.15:8000  (Share with other machines on LAN)
  Admin Dashboard:    http://localhost:8000/admin
  API Documentation:  http://localhost:8000/docs
  Listening Interface:http://0.0.0.0:8000
========================================================================
```

### Bước 2: Mở Port tường lửa (Windows Firewall) nếu bị chặn
Nếu thí sinh trên máy khác không kết nối được vào `http://192.168.1.15:8000`, hãy mở port 8000 trên máy chủ (chỉ cần chạy 1 lần trong PowerShell Admin):

```powershell
New-NetFirewallRule -DisplayName "Battlecode RPS Platform" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Bước 3: Cung cấp địa chỉ cho thí sinh
Gửi đường dẫn **`http://<LAN_IP>:8000`** (ví dụ: `http://192.168.1.15:8000`) cho tất cả thí sinh trong phòng thi đấu. Thí sinh chỉ cần mở trình duyệt lên là có thể đăng ký tài khoản và nộp bot.

---

## 3. Vận Hành Giải Đấu Hàng Ngày (Vòng Bảng Ngày 1 đến Ngày $n$)

### 3.1 Truy cập Trang Quản Trị (Admin Dashboard)
1. Truy cập: [http://localhost:8000/admin](http://localhost:8000/admin) (hoặc qua menu `Admin` trên thanh điều hướng).
2. Đăng nhập bằng tài khoản Admin.

### 3.2 Quản lý Cổng Đấu Tự Do FFA
- **Mở/Đóng cổng thủ công**: Admin có thể gạt công tắc **"Mở cổng thi đấu"** để mở hoặc đóng quyền thách đấu của thí sinh bất kỳ lúc nào.
- **Hệ số nhân Elo hôm nay ($x$)**:
  - Nhập hệ số $x$ (ví dụ: `1.5`, `2.0`, `2.5`).
  - Điểm Elo tăng/giảm sau mỗi trận đấu sẽ nhân trực tiếp với $x$:
    $$\Delta\text{Elo} = \text{round}(x \times 32 \times (S - E))$$
  - Điều này tạo động lực cho thí sinh thi đấu tích cực vào các ngày có hệ số thưởng cao.
- **Cập nhật ngày thi đấu**: Tăng chỉ số ngày hiện tại (`current_day`) từ 1 đến $n$.

---

## 4. Vận Hành Ngày Chung Kết (Ngày $n+1$: Bracket Playoff)

Vào ngày cuối cùng của giải đấu:
1. **Đóng cổng thi đấu FFA**: Khóa toàn bộ quyền nộp code mới và thách đấu tự do.
2. **Tạo Cây Đấu Loại Trực Tiếp (Generate Bracket)**:
   - Trên trang Admin, bấm nút **"Tạo sơ đồ thi đấu Playoff (Top 8 / Top 16)"**.
   - Hệ thống tự động lấy Top 8 hoặc Top 16 người chơi có điểm Elo cao nhất trên Bảng Xếp Hạng và phân hạt giống theo chuẩn cờ:
     - Trận 1: Hạt giống 1 gặp Hạt giống 8
     - Trận 2: Hạt giống 4 gặp Hạt giống 5
     - Trận 3: Hạt giống 2 gặp Hạt giống 7
     - Trận 4: Hạt giống 3 gặp Hạt giống 6
3. **Theo dõi sơ đồ thi đấu**:
   - Thí sinh và khán giả có thể xem diễn biến và kết quả các cặp đấu tại trang [http://localhost:8000/bracket](http://localhost:8000/bracket).
4. **Công thức tính điểm tổng kết giải**:
   $$\text{Tổng Điểm} = 0.5 \times \text{Điểm Elo chuẩn hóa} + 0.5 \times \text{Điểm thành tích Bracket}$$

---

## 5. Sao Lưu & Bảo Trì Dữ Liệu

- **Dữ liệu tài khoản & trận đấu**: Lưu trữ trong file CSDL SQLite [`app.db`](../app.db). Để backup, chỉ cần copy file `app.db` sang nơi an toàn.
- **File Replay trận đấu**: Toàn bộ lịch sử các ván đấu được lưu dưới dạng file JSON chuẩn tại thư mục `replays/match_<id>.json`.
- **Mã nguồn bot của thí sinh**: Lưu trữ tại `bots/<user_id>_<filename>.py`.
- **Reset giải đấu**: Nếu muốn tổ chức mùa giải mới từ đầu, xóa file `app.db`, thư mục `bots/` và `replays/`, sau đó khởi động lại bằng `python main.py`.
