/*
 * BoardView: draws any platform board (RPS 9x9, Connect Four, Caro) into a
 * container and reports clicks as (row, col). Used by the in-browser play page
 * and by the replay viewer for grid games, so both look identical.
 *
 * Board orientation:
 * - Grid games draw row 0 at the top (same as the Python board list).
 * - RPS 9x9 draws rank 9 (row 8) at the top, like the classic replay viewer.
 */
(function (global) {
  'use strict';

  const ICONS = { R: '<img class="rps-symbol" src="/static/img/rps-rock.svg" alt="Búa" draggable="false">', P: '<img class="rps-symbol" src="/static/img/rps-paper.svg?v=hand-2" alt="Bao" draggable="false">', S: '<img class="rps-symbol" src="/static/img/rps-scissors.svg" alt="Kéo" draggable="false">' };
  const FILES = 'abcdefghi';

  class BoardView {
    /**
     * @param {HTMLElement} container element that will hold the board
     * @param {string} slug game slug ('connect4' | 'caro' | 'rps9x9')
     * @param {number} rows board rows
     * @param {number} cols board columns
     * @param {function(number, number)} [onClick] cell click handler
     */
    constructor(container, slug, rows, cols, onClick) {
      this.container = container;
      this.slug = slug;
      this.rows = rows;
      this.cols = cols;
      this.onClick = onClick || null;
      this.cells = [];
      this.build();
    }

    build() {
      this.container.innerHTML = '';
      this.container.className = `gboard gboard-${this.slug}`;
      this.container.style.setProperty('--gcols', this.cols);
      this.container.style.setProperty('--grows', this.rows);
      this.cells = Array.from({ length: this.rows }, () => Array(this.cols));
      const rowOrder = [...Array(this.rows).keys()];
      if (this.slug === 'rps9x9') rowOrder.reverse();
      for (const r of rowOrder) {
        for (let c = 0; c < this.cols; c++) {
          const cell = document.createElement('button');
          cell.type = 'button';
          cell.className = 'gcell';
          cell.dataset.row = r;
          cell.dataset.col = c;
          if (this.slug === 'rps9x9') {
            cell.classList.add((r + c) % 2 === 0 ? 'dark' : 'light');
            cell.setAttribute('aria-label', FILES[c] + (r + 1));
            if (r === 8 && c === 8) cell.classList.add('goal-p1');
            if (r === 0 && c === 0) cell.classList.add('goal-p2');
          } else {
            cell.setAttribute('aria-label', `hàng ${r}, cột ${c}`);
          }
          cell.addEventListener('click', () => this.onClick && this.onClick(r, c));
          this.container.appendChild(cell);
          this.cells[r][c] = cell;
        }
      }
    }

    /**
     * Draw a board state.
     * @param {Array<Array>} board ints (grid games) or piece dicts/null (RPS)
     * @param {Object} [marks] {last: [r,c], from: [r,c], line: [[r,c]...],
     *   selected: [r,c], targets: [[r,c]...]}
     */
    render(board, marks) {
      marks = marks || {};
      const key = (rc) => rc ? rc[0] + ',' + rc[1] : '';
      const line = new Set((marks.line || []).map(key));
      const targets = new Set((marks.targets || []).map(key));
      for (let r = 0; r < this.rows; r++) {
        for (let c = 0; c < this.cols; c++) {
          const cell = this.cells[r][c];
          const k = r + ',' + c;
          const value = board[r][c];
          cell.classList.toggle('is-last', key(marks.last) === k);
          cell.classList.toggle('is-from', key(marks.from) === k);
          cell.classList.toggle('is-win', line.has(k));
          cell.classList.toggle('is-selected', key(marks.selected) === k);
          cell.classList.toggle('is-target', targets.has(k));
          // Only touch cells whose content changed, so the drop animation
          // plays for the newly placed stone and not for the whole board.
          const sig = value ? (this.slug === 'rps9x9' ? value.player + value.type : String(value)) : '';
          if (cell.dataset.sig === sig) continue;
          cell.dataset.sig = sig;
          if (this.slug === 'rps9x9') {
            cell.innerHTML = value
              ? `<span class="gpiece p${value.player}"><span class="icon">${ICONS[value.type] || value.type}</span></span>`
              : '';
          } else {
            cell.innerHTML = value ? `<span class="gstone p${value}"></span>` : '';
          }
        }
      }
    }

    setInteractive(on) {
      this.container.classList.toggle('is-interactive', !!on);
    }
  }

  global.BoardView = BoardView;
})(window);
