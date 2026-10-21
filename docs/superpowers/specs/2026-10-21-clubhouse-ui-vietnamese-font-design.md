# Design Spec: Unified Clubhouse 2.0, Vietnamese Typography & Student-Friendly Guide

## 1. Overview & Objectives
This specification defines the architectural design for standardizing the CodeDuel web interface into the **Unified Clubhouse 2.0** theme. The goals are:
1. **Fix Vietnamese Font Rendering**: Eliminate all font-rendering glitches and glyph fallbacks by standardizing on `Be Vietnam Pro` (display & UI body) and `JetBrains Mono` (code & data numbers).
2. **Consolidate Clubhouse Design Tokens**: Harmonize stylesheets (`style.css`, `arena-light.css`, `site.css`, `clubhouse.css`), removing abusive `!important` declarations and bringing pages like `/bracket`, `/replay/<id>`, and `/admin` into the cohesive Clubhouse aesthetic.
3. **Human & Student-Friendly Guide (`guide.html`)**: Rewrite the platform guide to be welcoming, encouraging, and intuitive for university students learning network programming and bot development.
4. **Zero-Node.js & Mobile Accessibility**: Preserve zero-Node.js constraints, ensure touch targets ≥ 44×44px, and eliminate mobile horizontal overflow from CSS rotations.

---

## 2. Typography Architecture
### 2.1 The Root Cause of Vietnamese Font Glitches
Previously, stylesheets specified:
- `style.css`: `--font-display: "Bahnschrift", "DIN Alternate", ...;`
- `clubhouse.css`: `--font-sans: "Trebuchet MS", ...; --font-display: "Trebuchet MS", ...;`
Neither `Bahnschrift` nor `Trebuchet MS` has complete Vietnamese diacritics glyph coverage in Windows/web engines. When rendering characters such as `ơ`, `ư`, `đ`, `ế`, `ả`, `ặ`, `ỗ`, the browser falls back to system fonts (Arial/Times), resulting in visible weight mismatches and baseline jumping.

### 2.2 Standardized Typography Stack
- **Web Font Delivery**: Preconnect and load `Be Vietnam Pro` and `JetBrains Mono` from Google Fonts with `display=swap` and full Vietnamese subset support in `web/templates/base.html`:
  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,600&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  ```
- **CSS Font Tokens**:
  - `--font-sans: "Be Vietnam Pro", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;`
  - `--font-display: "Be Vietnam Pro", sans-serif;`
  - `--font-mono: "JetBrains Mono", "Cascadia Code", Consolas, monospace;`

---

## 3. Visual System: Unified Clubhouse 2.0
### 3.1 Design Palette & Tokens
- Canvas / Main Background: `#faf5e9` (warm paper cream, subtle radial dot texture)
- Surface / Cards: `#fffdf6` (bright warm white)
- Ink / Text / Borders: `#29352d` (deep forest charcoal)
- Accent 1 (Playful Amber): `#ffcf56` (trophy yellow, badges, highlights)
- Accent 2 (Club Blue): `#355eae` (primary CTA, active navigation)
- Player 1 (Coral Red): `#e9876a` / `#f85149`
- Player 2 (Sky Cornflower): `#6c94c5` / `#58a6ff`
- Neutral Muted: `#5f685c`
- Borders & Shadows:
  - `--border: 2px solid #29352d;`
  - `--shadow-1: 3px 4px 0 #29352d;`
  - `--shadow-2: 5px 7px 0 #29352d;`
  - `--radius: 14px;`
  - `--radius-lg: 20px;`

### 3.2 Component Consistency Across Specialized Pages
- **Replay & Live Visualizer (`/replay/<id>`, `/games/<game>/live`)**: The 9×9 board container receives a clean Clubhouse card frame with ink border and hard shadow. Coordinate labels (A-I, 1-9) use `--font-mono`.
- **Bracket View (`/bracket`)**: Bracket match nodes, tournament tree lines, and winner badges use Clubhouse card tokens instead of raw dark slate.
- **Admin Panel (`/admin`)**: Management tables, toggle buttons, and portal status switches inherit the clean ink-bordered card style.
- **Mobile Polish**: Any `transform: rotate(...)` on stickers/badges must use `@media (max-width: 640px) { transform: none; }` or restricted bounds to prevent horizontal scroll bars.

---

## 4. Student-Friendly Guide Revamp (`guide.html`)
### 4.1 Pedagogical Approach
Transform the guide from a dry reference into an engaging, empathetic mentorship walkthrough:
- **Tone**: Warm, encouraging, Vietnamese-first ("Chào bạn! Hãy cùng xây dựng chú bot đầu tiên...").
- **Phase 1: Luật chơi Oẳn Tù Tì 9×9 trong 60 giây**: Búa, Bao, Kéo di chuyển 1 ô, ăn quân đối phương theo quy tắc kinh điển, hướng về góc đích của đối thủ để giành chiến thắng.
- **Phase 2: Bộ công cụ Starter Kit & File quan trọng**: Hướng dẫn mở file `bot_template.py`, giải thích hàm `get_move(board, my_player, history)`.
- **Phase 3: Dữ liệu truyền vào hàm có gì?**:
  - `board`: ma trận 9×9, ý nghĩa các ký hiệu quân (`R1`, `P1`, `S1`, `R2`, `P2`, `S2`).
  - `my_player`: bạn là Người chơi 1 hay Người chơi 2.
  - `history`: nhật ký các nước đi trước.
- **Phase 4: Các cấp độ thuật toán bot (Level 1 → Level 3)**:
  - *Level 1 (Tập đi)*: Random move hợp lệ.
  - *Level 2 (Săn mồi)*: Ưu tiên ăn quân đối phương nếu nằm trong tầm với.
  - *Level 3 (Chiến thuật)*: Di chuyển hướng về góc đối phương, bảo vệ quân chủ lực.
- **Phase 5: Kiểm tra cục bộ & Nộp bot**: Chạy `python local_arena.py` để đấu thử, sau đó nộp file `.py` lên hệ thống.
- **Phase 6: Câu hỏi thường gặp (FAQ)**: Xử lý timeout 1.0s, tránh crash, cách đọc log lỗi.

---

## 5. Non-Functional & Verification Constraints
- **Zero-Node.js**: Pure CSS, HTML5 templates, Vanilla JS.
- **Automated Tests**: All 416 existing tests must pass (`pytest -v`). New template rendering tests to verify web font links and guide page integrity.
- **Accessibility & UX**: Contrast ratios ≥ 4.5:1, button interactive targets ≥ 44×44px.
