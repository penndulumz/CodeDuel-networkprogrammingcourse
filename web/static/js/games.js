/*
 * Browser-side rule engines for every platform game, plus simple computer
 * opponents. They mirror the Python engines (engine/game.py and
 * engine/games/grid.py) so students can learn a game by playing it in the
 * browser before writing a bot. Everything runs client-side: no server
 * round-trips, so the play page keeps working on a flaky LAN or offline.
 */
(function (global) {
  'use strict';

  // ------------------------------------------------------------ grid games

  const LINE_DIRS = [[0, 1], [1, 0], [1, 1], [1, -1]];

  /** Shared engine for Connect Four and Caro (see engine/games/grid.py). */
  class GridGame {
    constructor(cfg) {
      this.slug = cfg.slug;
      this.rows = cfg.rows;
      this.cols = cfg.cols;
      this.winLength = cfg.winLength;
      this.gravity = cfg.gravity;
      this.reset();
    }

    reset() {
      this.board = Array.from({ length: this.rows }, () => Array(this.cols).fill(0));
      this.turn = 1;
      this.history = [];
      this.winner = null;
      this.winReason = null;
      this.winningLine = [];
    }

    get over() { return this.winReason !== null; }

    legalMoves() {
      if (this.over) return [];
      const moves = [];
      if (this.gravity) {
        for (let c = 0; c < this.cols; c++) if (this.board[0][c] === 0) moves.push(c);
        return moves;
      }
      for (let r = 0; r < this.rows; r++)
        for (let c = 0; c < this.cols; c++)
          if (this.board[r][c] === 0) moves.push([r, c]);
      return moves;
    }

    landing(move) {
      if (!this.gravity) return move;
      for (let r = this.rows - 1; r >= 0; r--) if (this.board[r][move] === 0) return [r, move];
      return null;
    }

    isLegal(move) {
      if (this.over) return false;
      if (this.gravity) return Number.isInteger(move) && move >= 0 && move < this.cols && this.board[0][move] === 0;
      const [r, c] = move;
      return r >= 0 && r < this.rows && c >= 0 && c < this.cols && this.board[r][c] === 0;
    }

    play(move) {
      if (!this.isLegal(move)) return null;
      const player = this.turn;
      const [r, c] = this.landing(move);
      this.board[r][c] = player;
      const record = { turn: this.history.length + 1, player, move, cell: [r, c] };
      this.history.push(record);
      const line = this.lineThrough(r, c, player);
      if (line.length) {
        this.winner = player;
        this.winReason = 'line';
        this.winningLine = line;
      } else if (this.board.every(row => row.every(v => v !== 0))) {
        this.winReason = 'board_full';
      }
      this.turn = player === 1 ? 2 : 1;
      return record;
    }

    lineThrough(r, c, player) {
      for (const [dr, dc] of LINE_DIRS) {
        const cells = [[r, c]];
        for (const s of [1, -1]) {
          let rr = r + dr * s, cc = c + dc * s;
          while (rr >= 0 && rr < this.rows && cc >= 0 && cc < this.cols && this.board[rr][cc] === player) {
            cells.push([rr, cc]);
            rr += dr * s; cc += dc * s;
          }
        }
        if (cells.length >= this.winLength) return cells;
      }
      return [];
    }

    /** Longest run (and open ends) player would get by owning (r, c). */
    runAt(r, c, player) {
      let score = 0;
      for (const [dr, dc] of LINE_DIRS) {
        let count = 1, open = 0;
        for (const s of [1, -1]) {
          let rr = r + dr * s, cc = c + dc * s;
          while (rr >= 0 && rr < this.rows && cc >= 0 && cc < this.cols && this.board[rr][cc] === player) {
            count++; rr += dr * s; cc += dc * s;
          }
          if (rr >= 0 && rr < this.rows && cc >= 0 && cc < this.cols && this.board[rr][cc] === 0) open++;
        }
        if (count >= this.winLength) score += 100000;
        else if (open > 0) score += Math.pow(10, count) * open;
      }
      return score;
    }
  }

  /** Pattern-scoring computer player shared by both grid games. */
  function gridAiMove(game, level) {
    const me = game.turn, opp = me === 1 ? 2 : 1;
    let moves = game.legalMoves();
    if (!game.gravity) {
      // Only consider cells near existing stones to keep Caro fast.
      const near = moves.filter(([r, c]) => {
        for (let dr = -2; dr <= 2; dr++) for (let dc = -2; dc <= 2; dc++) {
          const rr = r + dr, cc = c + dc;
          if (rr >= 0 && rr < game.rows && cc >= 0 && cc < game.cols && game.board[rr][cc] !== 0) return true;
        }
        return false;
      });
      moves = near.length ? near : [[Math.floor(game.rows / 2), Math.floor(game.cols / 2)]];
    }
    if (level === 'easy') {
      // Easy: still takes an immediate win, otherwise plays randomly.
      for (const m of moves) {
        const [r, c] = game.landing(m);
        if (game.runAt(r, c, me) >= 100000) return m;
      }
      return moves[Math.floor(Math.random() * moves.length)];
    }
    let best = moves[0], bestScore = -Infinity;
    for (const m of moves) {
      const [r, c] = game.landing(m);
      let score = game.runAt(r, c, me) * 1.1 + game.runAt(r, c, opp);
      if (game.gravity) {
        score -= Math.abs(c - (game.cols - 1) / 2) * 3;
        // Do not hand the opponent a winning cell directly above our stone.
        if (r > 0) {
          game.board[r][c] = me;
          if (game.runAt(r - 1, c, opp) >= 100000) score -= 50000;
          game.board[r][c] = 0;
        }
      }
      score += Math.random();
      if (score > bestScore) { bestScore = score; best = m; }
    }
    return best;
  }

  // ------------------------------------------------------------ RPS chess 9x9

  const RPS_BEATS = { R: 'S', S: 'P', P: 'R' };
  const RPS_GOALS = { 1: [8, 8], 2: [0, 0] };
  const RPS_DIRS = [[-1, -1], [-1, 0], [-1, 1], [0, -1], [0, 1], [1, -1], [1, 0], [1, 1]];
  const RPS_FILES = 'abcdefghi';

  /** Mirror of engine/game.py (standard variant). */
  class RpsGame {
    constructor() {
      this.slug = 'rps9x9';
      this.rows = 9;
      this.cols = 9;
      this.maxTurns = 200;
      this.reset();
    }

    reset() {
      const p1 = ['R', 'R', 'R', 'P', 'P', 'P', 'S', 'S', 'S'];
      const p2 = ['S', 'S', 'S', 'P', 'P', 'P', 'R', 'R', 'R'];
      this.board = Array.from({ length: 9 }, () => Array(9).fill(null));
      for (let c = 0; c < 9; c++) {
        this.board[0][c] = { type: p1[c], player: 1 };
        this.board[8][c] = { type: p2[c], player: 2 };
      }
      this.turn = 1;
      this.history = [];
      this.winner = null;
      this.winReason = null;
    }

    get over() { return this.winReason !== null; }

    count(player, type) {
      let n = 0;
      for (const row of this.board) for (const p of row)
        if (p && p.player === player && (!type || p.type === type)) n++;
      return n;
    }

    destinations(r, c) {
      const piece = this.board[r][c];
      if (!piece || piece.player !== this.turn || this.over) return [];
      const out = [];
      for (const [dr, dc] of RPS_DIRS) {
        const tr = r + dr, tc = c + dc;
        if (tr < 0 || tr > 8 || tc < 0 || tc > 8) continue;
        const t = this.board[tr][tc];
        if (!t || (t.player !== piece.player && RPS_BEATS[piece.type] === t.type)) out.push([tr, tc]);
      }
      return out;
    }

    legalMoves() {
      const moves = [];
      for (let r = 0; r < 9; r++) for (let c = 0; c < 9; c++)
        for (const to of this.destinations(r, c)) moves.push([[r, c], to]);
      return moves;
    }

    play(move) {
      const [[fr, fc], [tr, tc]] = move;
      if (!this.destinations(fr, fc).some(([r, c]) => r === tr && c === tc)) return null;
      const piece = this.board[fr][fc];
      const captured = this.board[tr][tc];
      this.board[tr][tc] = piece;
      this.board[fr][fc] = null;
      const player = piece.player;
      const sq = (r, c) => RPS_FILES[c] + (r + 1);
      const record = {
        turn: this.history.length + 1, player, from: [fr, fc], to: [tr, tc],
        piece: piece.type, captured: captured ? captured.type : null,
        san: `${piece.type}${sq(fr, fc)}${captured ? 'x' : '-'}${sq(tr, tc)}`,
      };
      this.history.push(record);
      const goal = RPS_GOALS[player];
      if (tr === goal[0] && tc === goal[1]) {
        this.winner = player; this.winReason = 'goal';
      } else if (captured && this.count(captured.player, captured.type) === 0) {
        this.winner = player; this.winReason = 'wipeout';
      } else if (this.history.length >= this.maxTurns) {
        const a = this.count(1), b = this.count(2);
        this.winReason = 'max_turns';
        this.winner = a > b ? 1 : b > a ? 2 : null;
      }
      if (!this.over) {
        this.turn = player === 1 ? 2 : 1;
        if (this.legalMoves().length === 0) { this.winReason = 'stalemate'; this.winner = null; }
      }
      return record;
    }
  }

  /** Greedy computer player for RPS: win > capture > advance towards goal. */
  function rpsAiMove(game, level) {
    const me = game.turn;
    const moves = game.legalMoves();
    if (level === 'easy') {
      const winning = moves.find(([, to]) => to[0] === RPS_GOALS[me][0] && to[1] === RPS_GOALS[me][1]);
      return winning || moves[Math.floor(Math.random() * moves.length)];
    }
    const goal = RPS_GOALS[me];
    let best = moves[0], bestScore = -Infinity;
    for (const mv of moves) {
      const [[fr, fc], [tr, tc]] = mv;
      const piece = game.board[fr][fc];
      const target = game.board[tr][tc];
      let score = 0;
      if (tr === goal[0] && tc === goal[1]) score += 10000;
      if (target) {
        score += 50;
        if (game.count(target.player, target.type) === 1) score += 5000;
      }
      const before = Math.max(Math.abs(goal[0] - fr), Math.abs(goal[1] - fc));
      const after = Math.max(Math.abs(goal[0] - tr), Math.abs(goal[1] - tc));
      score += (before - after) * 8;
      // Avoid stepping next to an enemy piece that beats us.
      for (const [dr, dc] of RPS_DIRS) {
        const rr = tr + dr, cc = tc + dc;
        if (rr < 0 || rr > 8 || cc < 0 || cc > 8) continue;
        const n = game.board[rr][cc];
        if (n && n.player !== me && RPS_BEATS[n.type] === piece.type) score -= 30;
      }
      score += Math.random() * 4;
      if (score > bestScore) { bestScore = score; best = mv; }
    }
    return best;
  }

  // ------------------------------------------------------------ registry

  const GameKit = {
    create(slug) {
      if (slug === 'connect4') return new GridGame({ slug, rows: 6, cols: 7, winLength: 4, gravity: true });
      if (slug === 'caro') return new GridGame({ slug, rows: 15, cols: 15, winLength: 5, gravity: false });
      if (slug === 'rps9x9') return new RpsGame();
      throw new Error('Unknown game: ' + slug);
    },
    aiMove(game, level) {
      return game.slug === 'rps9x9' ? rpsAiMove(game, level) : gridAiMove(game, level);
    },
    ICONS: { R: '<img class="rps-symbol" src="/static/img/rps-rock.svg" alt="Búa">', P: '<img class="rps-symbol" src="/static/img/rps-paper.svg?v=hand-2" alt="Bao">', S: '<img class="rps-symbol" src="/static/img/rps-scissors.svg" alt="Kéo">' },
  };

  global.GameKit = GameKit;
})(window);
