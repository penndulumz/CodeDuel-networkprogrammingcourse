# Battlecode RPS 9x9 — Master Context Resume for AI Agents & Team

> **Muc dich cua file nay**: Day la file "bo nho ngu canh trung tam" (Single Source of Truth - SSOT).
> Khi bat ky thanh vien nao trong nhom (Member 1, 2, 3, 4) lam viec voi bat ky AI nao (Claude, Gemini, GPT, Cursor AI, DeepSeek...), hay nap file nay vao de AI ngay lap tuc nam duoc 100% kien truc, quy uoc va nhiem vu ma khong bi quen hoac lam sai lech he thong.

---

## 1. Tom Tat Du An (System Overview)
- **Ten du an**: Battlecode RPS Chess 9x9 Platform.
- **Mo ta**: Nen tang thi dau co Oan Tu Ti (Rock-Paper-Scissors) kich thuoc 9x9 cho sinh vien. Sinh vien viet bot bang Python de dieu khien cac quan co dau 1v1.
- **Mo hinh may chu**: Centralized Runner. Nguoi choi upload file bot Python len web. Server luu ma nguon kin dao (chong lo code), chay ngam tran dau trong tien trinh con co lap, xuat file replay JSON va cap nhat diem Elo.
- **The thuc giai dau**:
  - **Ngay 1 den Ngay n**: Mo cong theo khung gio dong duoc cau hinh qua co so du lieu (mac dinh 19h - 21h). Dau tu do FFA khong gioi han. Moi ngay co mot he so nhan Elo ngau nhien x in [1.0, 3.0].
  - **Ngay n+1**: Dau bang loai truc tiep (Bracket BO3) giua cac top bot de tim nha vo dich.
  - **Diem tong ket**: Ket hop giua Elo tich luy va thu hang giai dau ngay cuoi.
- **Tech Stack**:
  - **Backend & Engine**: Python 3.10+, FastAPI, SQLite (qua SQLAlchemy WAL), PyYAML.
  - **Frontend**: HTML5, Vanilla JavaScript, CSS3 Design Tokens (bang mau toi Charcoal/Slate chuyen nghiep), khong dung Node.js/npm.
  - **Deployment**: Local-First & Multi-Machine LAN (`python main.py` lang nghe tren `0.0.0.0:8000` voi co che tu dong do IP mang LAN `http://<LAN_IP>:8000`), khong phu thuoc dich vu dam may ngoai.

---

## 2. Luat Game Oan Tu Ti 9x9 & Bot Interface

### 2.1 Ban co va Toa do
- Ban co 9x9: `row`: 0 den 8 (tuong ung Rank 1 den 9), `col`: 0 den 8 (tuong ung File a den i).
- Cac quan co: `'R'` (Dam / Rock), `'P'` (La / Paper), `'S'` (Keo / Scissors).
- Khac che: `R > S`, `S > P`, `P > R`. Cung loai thi chan nhau. Thua RPS thi khong duoc di vao.
- **Bo tri xuat phat**:
  - Player 1 (Do): Hang 0 (rank 1) gom `['R','R','R','P','P','P','S','S','S']`. O dich can den: `i9` (`row=8, col=8`).
  - Player 2 (Xanh): Hang 8 (rank 9) gom `['S','S','S','P','P','P','R','R','R']`. O dich can den: `a1` (`row=0, col=0`).
- **Nuoc di**: Di 1 o theo 8 huong (ngang, doc, cheo nhu quan Vua trong co vua).
- **Thang**: Cham o dich cua doi thu HOAC diet sach ca 3 quan cua 1 loai (R, P, hoac S) cua doi thu.
- **Timeout**: Toi da 1.0 giay/turn. Toi da 200 turns/tran.

### 2.2 Bot Python Interface (`bot.py`)
Moi bot sinh vien viet phai co signature chuan sau:

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

## 3. Cau Truc File Replay JSON (`replays/match_<id>.json`)
Moi tran dau sau khi ket thuc se sinh file replay JSON co dinh dang chuan:

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

## 4. Phan Chia Cong Viec 4 Thanh Vien (Roles & Responsibilities)

1. **Member 1 (Engine Lead)**:
   - Quan ly: `engine/game.py`, `engine/sandbox.py`, `starter_kit/`, `tests/test_game.py`, `tests/test_sandbox.py`.
   - Nhiem vu: Xay dung luat co, kiem tra di chuyen hop le, sandbox AST chan ma doc (74 mau tan cong), bo starter kit cho sinh vien tu test offline.
2. **Member 2 (Execution Lead)**:
   - Quan ly: `engine/runner.py`, `server/queue.py`, `tests/test_runner.py`.
   - Nhiem vu: Chay van dau giua 2 file bot, giam sat tien trinh con, timeout 1.0s, bat loi crash, tao file `replays/match_<id>.json`.
3. **Member 3 (Backend & Tournament Lead)**:
   - Quan ly: `server/models.py`, `server/routes/`, `server/tournament.py`, `server/boss_manager.py`, `server/bosses/`, `config/tournament.yaml`.
   - Nhiem vu: API xac thuc, luu bot, hang doi thach dau FFA, cong thuc tinh Elo nhan he so x, quan ly Boss Arena, bo danh gia lich trinh dong va boc tham bang Bracket.
4. **Member 4 (Frontend & Visualizer Lead)**:
   - Quan ly: `web/templates/`, `web/static/js/visualizer.js`, `web/static/css/`.
   - Nhiem vu: Bang xep hang Elo (Leaderboard), trang ho so nguoi choi & nop code, visualizer ban co 9x9 xem replay muot ma voi design tokens Charcoal, trang quan tri admin bao mat.

---

## 5. Quy Uoc Lap Trinh Bat Buoc (Coding Standards)
1. **Comment**: Bat buoc comment code bang **Tieng Anh ro rang, de hieu**. Giai thich ly do thiet ke o cac logic phuc tap.
2. **Khong tu y them thu vien ngoai**: Uu tien thu vien chuan cua Python (`math`, `random`, `json`, `ast`, `subprocess`, `dataclasses`). Thu vien ngoai chi dung nhung goi da co trong `requirements.txt`.
3. **An toan & Kiem thu (TDD)**: Viet ham nao phai co unit test kiem thu ham do trong thu muc `tests/`.
4. **Human-in-the-loop**: Khi AI tao code, thanh vien phai tu chay lenh kiem tra tren terminal truoc khi cap nhat `TASKS.md` va commit git.

---

## 6. Master Prompts Danh Cho Thanh Vien Sao Chep Cho AI

### Master Prompt 1: Khoi dau mot phien lam viec moi
> *"Toi la **Member [Dien 1, 2, 3 hoac 4]** trong nhom phat trien du an **Battlecode RPS 9x9**. Du an dang to chuc theo tai lieu `docs/CONTEXT_RESUME.md` va `TASKS.md`. Hay doc 2 file do de nam ro toan bo kien truc he thong, cac interface chuan va quy uoc lap trinh. Bay gio, toi can ban ho tro toi thuc hien **Task [Dien ma task, vi du 1.2]** trong `TASKS.md`. Hay giai thich ngan gon, truc quan va viet code chuan voi comment tieng Anh chi tiet."*

### Master Prompt 2: Nho AI debug loi
> *"Toi gap loi nay khi chay lenh kiem thu [Dien lenh, vi du: pytest tests/test_game.py]: [Paste log loi vao day]. Hay doi chieu voi luat game va interface trong `docs/CONTEXT_RESUME.md` de tim nguyen nhan goc re va sua code giup toi mot cach toi gian nhat."*

---

## 7. Quy Tac Vong Lap & Quan Ly Breaking Changes (Continuous Feedback Loop Law)

> **QUY TAC BAT BUOC CHO MOI THANH VIEN VA MOI AI AGENT**:
> Du an van hanh theo mo hinh **Vong lap phat trien khep kin (Continuous Feedback Loop)**.

1. **Nguon Chan Ly Duy Nhat (Single Source of Truth - SSOT)**:
   - File `docs/CONTEXT_RESUME.md` nay la **NGUON SU THAT TOI CAO DUY NHAT** chi phoi toan bo kien truc, CSDL, luat co, va workflow cua du an.
   - Cac file thiet lap rieng cho AI (nhu `GEMINI.md`, `CLAUDE.md`, `.cursorrules`...) **TUYET DOI KHONG DUOC TU Y DINH NGHIA RULES MOI HOAC TACH NHANH QUY UOC**. Chung phai luon tro ve `docs/CONTEXT_RESUME.md`.
2. **Quy Tac Cap Nhat Breaking Changes Ngay Lap Tuc**:
   - Khi co bat ky thay doi mang tinh buoc ngoat nao — bao gom: thay doi API endpoint, thay doi ham `get_move()`, sua doi luat game, thay doi schema database trong `server/models.py`, doi port, bo sung boss moi, hay thay doi cau hinh lich trinh — nguoi hoac AI thuc hien **BAT BUOC PHAI CAP NHAT TRUC TIEP VAO FILE NAY (`docs/CONTEXT_RESUME.md`) VA `TASKS.md` TRONG CUNG COMMIT DO**.
3. **Bao Toan Chu Trinh Cho Nguoi Den Sau**:
   - Neu ai do thay doi he thong ma khong cap nhat `docs/CONTEXT_RESUME.md`, phien lam viec tiep theo cua cac AI khac (Claude, Gemini, Cursor) se doc du lieu cu, gay ra xung dot phien ban va pha vo tinh lien tuc cua du an. Moi thay doi khong ghi vao day deu bi coi la khong hop le.

---

## 8. Quy Tac Bat Buoc Cach Ly Bang Git Worktrees (Mandatory Git Worktree Isolation)
1. **Luon dung Worktree khi phat trien tinh nang moi**:
   - Moi task moi hoac refactor lon bat buoc phai tao nhanh cach ly trong thu muc `.worktrees/<ten-nhanh>` thong qua ky nang `using-git-worktrees`.
   - Tuyet doi khong code truc tiep len nhanh `main` khi chua hoan thanh TDD va duoc review toan dien.
2. **Quy trinh ket thuc nhanh**:
   - Chi merge ve `main` sau khi toan bo test suite (`pytest -v`) dat 100% PASS va thuc hien clean up worktree dung chuan.

---

## 9. Bao Ton Tuyet Doi Thu Muc Goc & File Meta (Root Preservation Law)
1. **Thu muc `resources/` (Thu vien tham khao cua User)**:
   - `resources/` la thu muc chua tai lieu goc va cac du an mau cua User, da duoc dua vao `.gitignore`.
   - **BAT BIEN**: `resources/` CHI NAM DUY NHAT TAI THU MUC GOC (ROOT REPO). Tuyet doi khong di chuyen, khong xoa va KHONG DUOC DUPLICATE/COPY vao ben trong cac worktree `.worktrees/`.
2. **Cac thu muc va file meta**:
   - `.git/`, `.gemini/`, `GEMINI.md`, `CLAUDE.md`, va `docs/CONTEXT_RESUME.md` luon giu nguyen vi tri chuan o root.

---

## 10. Nguyen Tac Single-Admin & Trien Khai Da May (Multi-Machine LAN)
1. **Duy Nhat Mot Tai Khoan Quan Tri (Single-Admin Invariant)**:
   - He thong chi cho phep dung **1 tai khoan Admin toi cao**.
   - Cau hinh qua bien moi truong: `ADMIN_USERNAME` (mac dinh: `admin`), `ADMIN_PASSWORD` (mac dinh: `admin123`).
   - Moi no luc dang ky tai khoan mang ten `admin` (hoac trung `ADMIN_USERNAME`, khong phan biet hoa thuong) deu bi API tu choi voi ma loi HTTP 400.
   - Khi khoi dong seeder, bat ky tai khoan nao khac co `is_admin = True` deu tu dong bi ha quyen xuong `is_admin = False`.
2. **Kiem Soat Truy Cap Tuyen Admin (Route Authorization Guards)**:
   - Route `/admin` yeu cau xac thuc admin nghiem ngat.
   - Nguoi dung chua dang nhap truy cap `/admin` se bi chuyen huong HTTP 303 Redirect ve `/login?next=/admin`.
   - Nguoi dung da dang nhap nhung khong co quyen admin se nhan loi HTTP 403 Forbidden.
   - Thanh dieu huong (navbar) chi hien thi muc `Admin` khi nguoi dung hien tai co `is_admin = True`.
3. **Trien Khai Da May Qua Mang Noi Bo (LAN Access)**:
   - Server lang nghe tren moi giao dien mang (`0.0.0.0:8000`).
   - Banner khoi dong tu dong do IP mang noi bo cua may chu (`http://<LAN_IP>:8000`) de nguoi to chuc cung cap cho cac may tinh khac trong cung Wi-Fi/LAN truy cap thi dau.

---

## 11. Dau Truong Boss Benchmark Server-Side (`server/bosses/`, `server/boss_manager.py`)
He thong cung cap 5 bot chuan muc server-side (Server Bosses) dat tai thu muc `server/bosses/` nham phuc vu viec test bot, do suc tren Leaderboard va lam moc tham chieu:

1. **Level 1: Novice (`novice_bot.py`)**:
   - Slug: `novice`, Display Name: `[Boss] Level 1: Novice`, Default Elo: 1000.
   - Thuat toan: Chon ngay nuoc cham dich neu co, thuc hien an quan co loi neu co, con lai di chuyen ngau nhien hop le.
2. **Level 2: Rusher (`rusher_bot.py`)**:
   - Slug: `rusher`, Display Name: `[Boss] Level 2: Rusher`, Default Elo: 1200.
   - Thuat toan: Tinh khoang cach Chebyshev toi o dich (`i9` hoac `a1`), uu tien tuyet doi nuoc tien ve dich va ne tranh cac o bi quan dich khac che de doa.
3. **Level 3: Sentinel (`sentinel_bot.py`)**:
   - Slug: `sentinel`, Display Name: `[Boss] Level 3: Sentinel`, Default Elo: 1400.
   - Thuat toan: Phong thu vanh dai bao ve o dich nha, dong thoi theo doi va tap trung tieu diet loai quan co so luong it nhat cua doi thu de gianh chien thang Wipeout.
4. **Level 4: Tactician (`tactician_bot.py`)**:
   - Slug: `tactician`, Display Name: `[Boss] Level 4: Tactician`, Default Elo: 1600.
   - Thuat toan: Tim kiem Minimax 2 lop (2-ply) voi cat tia Alpha-Beta. Ham danh gia the tran can bang giua gia tri quan co, khoang cach toi o dich, ap luc de doa va vi tri an toan.
5. **Level 5: Apex Master (`apex_bot.py`)**:
   - Slug: `apex`, Display Name: `[Boss] Level 5: Apex Master`, Default Elo: 1800.
   - Thuat toan: Minimax do sau thich ung dong, ket hop bay quan (piece baiting), phan doan nuoc di tiep theo cua doi thu va hoi tu the tran tan cong ep goc.

**Quan Ly Trien Khai Boss (`server/boss_manager.py`)**:
- Chi Admin moi co quyen trien khai (`deploy_boss`) hoac go bo (`retract_boss`) cac Boss bot.
- Khi trien khai, he thong tao tai khoan User dai dien (vi du: username `boss_novice`, `boss_apex`), sao chep file bot vao `bots/` va gan bot hoat dong.
- API quan ly:
  - `GET /api/admin/bosses`: Tra ve danh sach tat ca boss va trang thai trien khai hien tai.
  - `POST /api/admin/bosses/deploy`: Trien khai hoac thu hoi boss dua tren tham so `slug` va `action` (`deploy` hoac `retract`).

---

## 12. Cau Hinh Lich Trinh Giai Dau Dong Trong CSDL (`TournamentSetting`)
He thong ho tro cau hinh lich trinh dong luu tru trong bang `TournamentSetting` cua CSDL SQLite, cho phep quan tri vien dieu chinh tren giao dien web ma khong can khoi dong lai server hay sua file YAML:

1. **Cac Khoa Cau Hinh Dong**:
   - `start_time`: Gio mo cong FFA hang ngay (dinh dang `HH:MM`, vi du `19:00`).
   - `end_time`: Gio dong cong FFA hang ngay (dinh dang `HH:MM`, vi du `21:00`).
   - `ffa_mode`: Che do mo cong:
     - `"auto"`: Mo/dong tu dong theo khung gio giua `start_time` va `end_time`.
     - `"true"`: Luon mo cong bat ke gio giac (Override Open).
     - `"false"`: Luon dong cong (Override Closed).
   - `elo_multiplier`: He so nhan Elo thuong hang ngay (gia tri tu 1.0 den 3.0).
   - `current_day`: Ngay thi dau hien tai (1 den n).
2. **Ham Danh Gia Trang Thai Cong (`is_ffa_portal_open`)**:
   - Nhap tham so: `config`, `current_time_str`, `db_settings`.
   - Xu ly linh hoat ca khung gio trong ngay (`19:00` den `21:00`) lan khung gio xuyen dem (`22:00` den `02:00`).

---

## 13. Thiet Ke Giao Dien Minimalist Charcoal & He Thong CSS Tokens
Giao dien web duoc thiet ke theo phong cach Minimalist Slate/Charcoal danh cho ky su va nha phat trien, loai bo toan bo mau neon va hieu ung gradient trang tri khong can thiet:

1. **Design Tokens (`web/static/css/style.css`)**:
   - `--bg-main: #0d1117`: Mau nen chinh toi gian.
   - `--bg-surface: #161b22`: Mau nen the card, bang, hop chua du lieu.
   - `--border-subtle: #30363d`: Duong vien tinh te 1px do tuong phan cao.
   - `--text-primary: #f0f6fc`: Chu chinh trang sang de doc.
   - `--text-muted: #8b949e`: Chu phu xam trung tinh.
2. **Visualizer Ban Co 9x9 Chuyen Nghiep**:
   - Thiet ke o co phang, net vien do ro rang.
   - Thanh dieu khien transport bar hien dai voi nut Play/Pause/Slider tinh gon.
   - Hien thi toa do a1 - i9 truc quan tren mep ban co.

---

## 14. He Thong Phan Tang Tai Lieu & Nguyen Tac Dong Bo Tuyet Doi

Tai lieu du an duoc to chuc theo he thong phan tang nghiem ngat, giu giong van hoc thuat, chuyen nghiep va khong chua bieu tuong trang tri (icons/emojis):

```text
+------------------------------------------------------------------------+
|                        README.md (Tang Tiep Nhan)                      |
|     Entrypoint duy nhat cho nguoi moi, Landing Page, Navigation Index  |
+-----------------------------------┬------------------------------------+
                                    | tro truc tiep den
+-----------------------------------v------------------------------------+
|                    docs/CONTEXT_RESUME.md (Tang SSOT)                  |
|       Nguon Chan Ly Duy Nhat Toi Cao — Quy dinh luat game, API, CSDL,  |
|         5 Boss Bots, Dynamic Schedule, vai tro 4 thanh vien va quy tac |
+──────────┬────────────────────────┬───────────────────────┬────────────+
           |                        |                       |
           v                        v                       v
+──────────────────────+ +──────────────────────+ +──────────────────────+
| docs/ARCHITECTURE.md | |  docs/BOT_GUIDE.md   | | docs/ADMIN_GUIDE.md  |
|  (Dac ta ky thuat)   | |  (Cam nang thi sinh) | | (Cam nang van hanh)  |
+──────────────────────+ +──────────────────────+ +──────────────────────+
           |                        |                       |
           +────────────────────────┼───────────────────────+
                                    |
+───────────────────────────────────v------------------------------------+
|                    TASKS.md (Tang Quan Tri Nhom)                       |
|    Bang theo doi tien do Milestones (0 den 8) & phan chia trach nhiem  |
|           (Danh cho con nguoi, giang vien cham diem & nghiem thu)      |
+───────────────────────────────────┬────────────────────────────────----+
                                    | anh xa chi tiet sang
+───────────────────────────────────v------------------------------------+
|         docs/superpowers/specs/ & docs/superpowers/plans/              |
|       Blueprint kien truc & Ke hoach thuc thi TDD chi tiet cho AI/Dev  |
+────────────────────────────────────────────────────────────────--------+
```

### 14.1 Vai Tro Cu The Cua Tung Tai Lieu
1. **`README.md` (Entry Point Bat Buoc)**:
   - **Muc dich**: Trang ha canh (Landing Page) cho nguoi moi, huong dan khoi chay trong 1 lenh (`python main.py`), ban do chi muc dieu huong va FAQ.
   - **Quy tac**: Tuyet doi khong nhoi nhet chi tiet code schema vao `README.md`. Moi chi tiet ky thuat cot loi dan link ve `docs/CONTEXT_RESUME.md`.
2. **`docs/CONTEXT_RESUME.md` (Single Source of Truth - SSOT)**:
   - **Muc dich**: Bo nho ngu canh trung tam cho toan bo nhom va moi AI Agent.
   - **Quy tac**: Day la tai lieu co tham quyen cao nhat. Moi thay doi kien truc, CSDL, luat game bat buoc phai cap nhat vao file nay dau tien.
3. **Bo tai lieu chuyen biet (`docs/ARCHITECTURE.md`, `docs/BOT_GUIDE.md`, `docs/ADMIN_GUIDE.md`)**:
   - Tach bach phuc vu chinh xac 3 doi tuong: Ky thuat vien/giao vien cham diem, Thi sinh viet bot, va Ban to chuc giai dau.
4. **Moi quan he giua `TASKS.md` va `docs/superpowers/`**:
   - `TASKS.md` la bang Kanban cap cao danh cho con nguoi va cham diem hoc phan theo cac Milestones tu 0 den 8.
   - `docs/superpowers/specs/` va `plans/` la tai lieu ky thuat vi mo danh cho lap trinh vien va AI thuc hien TDD.

### 14.2 Nguyen Tac Dong Bo Tuyet Doi (Continuous Documentation Sync)
- Khi co bat ky su thay doi nao ve: API (`get_move`, endpoint REST), CSDL (`server/models.py`), luat co, boss moi, hoac quy trinh trien khai:
  1. Cap nhat **ngay lap tuc** vao `docs/CONTEXT_RESUME.md` (SSOT).
  2. Cap nhat tai lieu chuyen biet tuong ung (`ARCHITECTURE.md`, `BOT_GUIDE.md`, hoac `ADMIN_GUIDE.md`).
  3. Cap nhat trang thai nghiem thu trong `TASKS.md`.
  4. Dam bao `README.md` giu vung vai tro la ban do chi muc dieu huong chinh xac.
