# 🤖 Cẩm Nang Thí Sinh: Lập Trình & Huấn Luyện Bot Cờ Oẳn Tù Tì 9×9

> **Dành cho**: Thí sinh, sinh viên tham gia giải đấu Battlecode RPS Platform.  
> **Khởi đầu nhanh**: Bạn chỉ cần tải thư mục [`starter_kit/`](../starter_kit/) về máy để bắt đầu lập trình và đấu thử offline mà không cần kết nối mạng.

---

## 1. Luật Chơi Cờ Oẳn Tù Tì 9×9 (Game Rules)

### 1.1 Bàn cờ và Tọa độ
- Bàn cờ hình vuông kích thước **9×9 ô**.
- **Chỉ số mảng Python**: `board[row][col]` với `row` từ `0` đến `8`, `col` từ `0` đến `8`.
- **Ký hiệu cờ vua**:
  - Hàng (Rank): `1` đến `9` (tương ứng `row = 0` đến `row = 8`).
  - Cột (File): `a` đến `i` (tương ứng `col = 0` đến `col = 8`).
  - Ô góc dưới bên trái là `a1` (`row=0, col=0`), ô góc trên bên phải là `i9` (`row=8, col=8`).

```text
    a   b   c   d   e   f   g   h   i
  +---+---+---+---+---+---+---+---+---+
9 | S | S | S | P | P | P | R | R | R |  <- Player 2 (Xanh) xuất phát tại Rank 9 (row 8)
8 |   |   |   |   |   |   |   |   |   |
7 |   |   |   |   |   |   |   |   |   |
6 |   |   |   |   |   |   |   |   |   |
5 |   |   |   |   |   |   |   |   |   |
4 |   |   |   |   |   |   |   |   |   |
3 |   |   |   |   |   |   |   |   |   |
2 |   |   |   |   |   |   |   |   |   |
1 | R | R | R | P | P | P | S | S | S |  <- Player 1 (Đỏ) xuất phát tại Rank 1 (row 0)
  +---+---+---+---+---+---+---+---+---+
    a   b   c   d   e   f   g   h   i
```

### 1.2 Quân cờ & Quy tắc tương khắc
Mỗi người chơi sở hữu 9 quân cờ gồm:
- **3 quân Đấm (Rock — `'R'` ✊)**
- **3 quân Lá (Paper — `'P'` ✋)**
- **3 quân Kéo (Scissors — `'S'` ✌)**

**Quy tắc khắc chế**:
$$\text{Đấm ('R')} \succ \text{Kéo ('S')}, \quad \text{Kéo ('S')} \succ \text{Lá ('P')}, \quad \text{Lá ('P')} \succ \text{Đấm ('R')}$$

- **Nước đi hợp lệ**: Mỗi quân đi 1 ô theo 8 hướng (ngang, dọc, chéo — như quân Vua trong cờ vua).
- **Quy tắc ăn quân**:
  - Bạn **CHỈ ĐƯỢC** đi vào ô có quân địch nếu quân của bạn **THẮNG** quân địch theo quy tắc Oẳn Tù Tì. Quân địch bị ăn sẽ bị loại khỏi bàn cờ.
  - Quân **CÙNG LOẠI** sẽ chặn nhau (không thể đi vào ô của nhau).
  - Quân **THUA** không được phép đi vào ô của quân thắng.
  - Tuyệt đối không được đi vào ô có quân cùng phe.

### 1.3 Điều kiện Thắng Cuộc
Một ván cờ kết thúc ngay lập tức khi xảy ra một trong các điều kiện sau:

1. 🚩 **Chạm ô đích (Goal Reach)**:
   - **Player 1 (Đỏ)**: Đưa bất kỳ quân nào chạm vào ô **`i9`** (`row=8, col=8`).
   - **Player 2 (Xanh)**: Đưa bất kỳ quân nào chạm vào ô **`a1`** (`row=0, col=0`).
2. 💥 **Diệt sạch quân (Wipeout Win)**:
   - Bạn ăn hết sạch toàn bộ **3 quân của bất kỳ 1 loại nào** của đối thủ (ví dụ: ăn hết 3 quân Đấm, HOẶC ăn hết 3 quân Lá, HOẶC ăn hết 3 quân Kéo của đối phương).
3. ⏱️ **Xử thua kỹ thuật (Technical Forfeit)**:
   - Bot đối thủ chạy quá **1.0 giây/turn** (`win_reason = 'timeout'`).
   - Bot đối thủ bị lỗi crash/ngoại lệ (`win_reason = 'error'`).
   - Bot đối thủ trả về nước đi không hợp lệ (`win_reason = 'invalid_move'`).
4. ⌛ **Hết 200 Lượt (Max Turns)**:
   - Sau 200 nước đi, bên nào còn tổng số quân trên bàn nhiều hơn sẽ thắng. Nếu bằng nhau, ván đấu có kết quả **Hòa (Draw)**.

---

## 2. Viết Bot Bằng Python (`my_bot.py`)

Bot của bạn là một file Python độc lập chứa hàm bắt buộc duy nhất `get_move`:

```python
"""my_bot.py — Bot chiến thuật của bạn."""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple

def get_move(
    board: List[List[Optional[Dict[str, any]]]], 
    my_player: int, 
    history: List[Dict[str, any]]
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Tính toán và trả về nước đi tiếp theo của bot.

    Args:
        board: Ma trận 9x9. Mỗi ô là None hoặc dict:
               {'type': 'R' | 'P' | 'S', 'player': 1 | 2}
        my_player: Số hiệu người chơi của bạn: 1 (Đỏ) hoặc 2 (Xanh).
        history: Danh sách các nước đi trước đó trong ván đấu:
                 [{'player': 1, 'from': (0, 3), 'to': (1, 3), 'piece': 'P', 'captured': None, 'san': '✋d1-d2'}]

    Returns:
        ((from_row, from_col), (to_row, to_col))
        Tọa độ ô xuất phát và ô đích (0 <= row <= 8, 0 <= col <= 8).
    """
    # 1. Tìm tất cả các quân của bạn trên bàn cờ
    # 2. Tìm nước đi hợp lệ tốt nhất
    # 3. Trả về tọa độ nước đi
    return ((0, 0), (1, 1))
```

---

## 3. Quy Định An Toàn & Bộ Lọc Sandbox AST

Khi upload bot lên hệ thống, mã nguồn sẽ được quét tĩnh tự động:

- ✅ **Các thư viện ĐƯỢC PHÉP dùng**:
  - `math`, `random`, `copy`, `collections`, `heapq`, `itertools`, `typing`, `dataclasses`.
- ❌ **Các thư viện BỊ CẤM TRIỆT ĐỂ**:
  - `os`, `sys`, `subprocess`, `socket`, `shutil`, `ctypes`, `threading`, `multiprocessing`, `requests`, `urllib`, `builtins`.
- ❌ **Các hàm & thao tác BỊ CẤM**:
  - `open()`, `eval()`, `exec()`, `compile()`, `globals()`, `locals()`, `__import__`.
  - Mọi hành vi truy cập dunder reflection: `__subclasses__`, `__builtins__`, `__globals__`, `__code__`, `__bases__`.

---

## 4. Kiểm Thử Bot Ngoại Tuyến (Offline Testing Với Local Arena)

Bạn không cần server để test bot! Trong thư mục `starter_kit/` có sẵn công cụ giả lập đấu giải:

```bash
# Đấu 10 trận giữa bot của bạn và bot heuristic mẫu
python starter_kit/local_arena.py my_bot.py starter_kit/heuristic_bot.py --rounds 10 --max-turns 150

# Đổi bên luân phiên giữa 2 bot (Player 1 <-> Player 2)
python starter_kit/local_arena.py my_bot.py starter_kit/heuristic_bot.py --rounds 10 --swap-sides
```

Output sẽ hiển thị chi tiết số trận thắng, tỷ lệ thắng theo Goal hay Wipeout, số turn trung bình và thời gian thực thi:
```text
============================================================
  TOURNAMENT RESULTS SUMMARY
============================================================
  my_bot              :   8 wins ( 80.0%)
  heuristic_bot       :   2 wins ( 20.0%)
  Draws               :   0      (  0.0%)
  Average Turns       : 48.3
============================================================
```

---

## 5. Mẹo & Chiến Thuật Thiết Kế Bot Đỉnh Cao

1. **Ưu tiên Goal Rush**: Nếu có bất kỳ quân nào chỉ cách ô đích (`i9` hoặc `a1`) 1 nước đi an toàn, hãy lập tức đi vào ô đích để kết thúc trận đấu.
2. **Săn Wipeout (Chiến thuật diệt chủng)**: Đối phương chỉ có 3 quân mỗi loại. Nếu một loại quân của đối thủ đã mất 2 quân, hãy dồn toàn lực săn lùng và tiêu diệt quân cuối cùng của loại đó để thắng ngay lập tức!
3. **Tránh bẫy tự sát (Suicide Avoidance)**: Trước khi di chuyển, luôn kiểm tra xem ô dự định đến có nằm trong tầm ăn của quân đối thủ ở lượt sau hay không.
4. **Bảo vệ quân yếu thế**: Không bao giờ để quân bị cô lập nếu xung quanh có quân đối thủ khắc chế.
5. **Tối ưu thời gian**: Bạn chỉ có 1.0 giây/turn. Sử dụng thuật toán Minimax với độ sâu hợp lý ($depth \le 3$) hoặc giải thuật heuristic đánh giá điểm thế trận theo trọng số.

---

## 6. Nộp Bot Lên Server Thi Đấu

1. Mở trình duyệt và truy cập địa chỉ máy chủ do ban tổ chức cung cấp (ví dụ: `http://192.168.1.15:8000` hoặc `http://localhost:8000`).
2. Đăng ký tài khoản tại menu **Đăng ký (Register)**.
3. Đăng nhập và truy cập trang **Hồ Sơ (Profile)**.
4. Chọn file `.py` của bạn và bấm **Upload Bot**.
5. Server sẽ tự động kiểm tra cú pháp và sandbox:
   - Nếu hợp lệ, bot sẽ được kích hoạt làm bot thi đấu chính thức.
   - Mã nguồn của bạn được bảo mật tuyệt đối, thí sinh khác hoàn toàn không thể xem code của bạn.
6. Khi cổng FFA mở (19:00 - 21:00), vào mục **Bảng Xếp Hạng (Leaderboard)** và bấm **Thách đấu** bất kỳ người chơi nào!
