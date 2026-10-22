// Render each active bracket pairing as a compact public scoreboard.
(function () {
  const container = document.getElementById('liveProjections');
  if (!container) return;
  const projectionStage = document.querySelector('.live-projections');
  const fullscreenButton = document.getElementById('projectionFullscreen');
  if (fullscreenButton && projectionStage) {
    fullscreenButton.addEventListener('click', async () => {
      if (document.fullscreenElement) {
        await document.exitFullscreen();
      } else if (projectionStage.requestFullscreen) {
        await projectionStage.requestFullscreen();
      }
    });
  }
  const autoAdvanceToggle = document.getElementById('autoAdvanceRounds');
  const startRoundButton = document.getElementById('startNextBracketRound');
  const controlMessage = document.getElementById('projectionControlMessage');
  let latestPairings = [];
  let roundRequestInFlight = false;
  const displayedTurns = new Map();
  const displayedGameIds = new Map();
  const progressKey = (matchId) => `bracketReplayProgress:${matchId}`;

  function getSavedProgress(matchId) {
    return Math.max(0, Number(localStorage.getItem(progressKey(matchId))) || 0);
  }

  if (autoAdvanceToggle) {
    autoAdvanceToggle.checked = sessionStorage.getItem('autoAdvanceBracketRounds') === 'true';
    autoAdvanceToggle.addEventListener('change', () => {
      sessionStorage.setItem('autoAdvanceBracketRounds', String(autoAdvanceToggle.checked));
      if (autoAdvanceToggle.checked) maybeAutoAdvance();
    });
  }
  if (startRoundButton) startRoundButton.addEventListener('click', queueNextRound);

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function buildBoard(initialBoard, moves) {
    const board = (initialBoard || []).map((row) => row.slice());
    moves.forEach((move) => {
      const piece = board[move.from[0]][move.from[1]] || {
        type: move.piece,
        player: move.player,
      };
      board[move.from[0]][move.from[1]] = null;
      board[move.to[0]][move.to[1]] = piece;
    });
    return board;
  }

  function renderBoard(board, lastMove) {
    const layout = element('div', 'projection-board-layout');
    const ranks = element('div', 'projection-ranks');
    for (let row = 9; row >= 1; row -= 1) ranks.appendChild(element('span', '', String(row)));
    const grid = element('div', 'projection-board');
    for (let row = 8; row >= 0; row -= 1) {
      for (let col = 0; col < 9; col += 1) {
        const piece = board[row] && board[row][col];
        const cell = element('span', `projection-cell ${(row + col) % 2 ? 'light' : 'dark'}`);
        cell.appendChild(element('small', 'projection-coordinate', `${String.fromCharCode(97 + col)}${row + 1}`));
        if (lastMove && lastMove.from[0] === row && lastMove.from[1] === col) cell.classList.add('last-from');
        if (lastMove && lastMove.to[0] === row && lastMove.to[1] === col) cell.classList.add('last-to');
        if ((row === 8 && col === 8) || (row === 0 && col === 0)) {
          cell.classList.add(row === 8 ? 'goal-p1' : 'goal-p2');
        }
        if (piece) {
          const token = element('span', `projection-piece player-${piece.player}`);
          const symbols = { R: 'rps-rock.svg', P: 'rps-paper.svg?v=hand-2', S: 'rps-scissors.svg' };
          const icon = document.createElement('img');
          icon.className = 'rps-symbol';
          icon.src = `/static/img/${symbols[piece.type] || symbols.R}`;
          icon.alt = piece.type;
          icon.draggable = false;
          token.appendChild(icon);
          cell.appendChild(token);
        }
        grid.appendChild(cell);
      }
    }
    const files = element('div', 'projection-files');
    for (let col = 0; col < 9; col += 1) files.appendChild(element('span', '', String.fromCharCode(97 + col)));
    layout.append(ranks, grid, files);
    return layout;
  }

  function renderCounts(board, player) {
    const counts = { R: 0, P: 0, S: 0 };
    board.forEach((row) => row.forEach((piece) => {
      if (piece && piece.player === player && counts[piece.type] !== undefined) counts[piece.type] += 1;
    }));
    const wrap = element('div', 'projection-counts');
    const symbols = { R: 'rps-rock.svg', P: 'rps-paper.svg?v=hand-2', S: 'rps-scissors.svg' };
    Object.entries(counts).forEach(([type, count]) => {
      const item = element('span', `projection-count${count ? '' : ' dead'}`);
      const icon = document.createElement('img');
      icon.src = `/static/img/${symbols[type]}`;
      icon.alt = type;
      item.append(icon, element('b', '', String(count)));
      wrap.appendChild(item);
    });
    return wrap;
  }

  function renderPairing(pairing) {
    const card = element('article', 'projection-card');
    const heading = element('div', 'projection-heading');
    heading.appendChild(element('strong', '', `${pairing.round_name} · Trận ${pairing.match_index}`));
    heading.appendChild(element('span', `projection-status ${pairing.status}`, pairing.status));
    card.appendChild(heading);

    const score = element(
      'div',
      'projection-score',
      `${pairing.player1}  ${pairing.score_p1} – ${pairing.score_p2}  ${pairing.player2}`
    );
    card.appendChild(score);

    if (pairing.current_game) {
      const game = pairing.current_game;
      const moves = game.moves || [];
      const shown = Math.min(displayedTurns.get(pairing.id) || 0, moves.length);
      const visibleMoves = moves.slice(0, shown);
      const board = buildBoard(pairing.initial_board, visibleMoves);
      const lastMove = visibleMoves.slice(-1)[0];
      const sides = element('div', 'projection-players');
      const p1 = element('section', 'projection-player p1');
      p1.append(element('strong', '', pairing.player1), element('small', '', 'Đỏ · P1'), renderCounts(board, 1));
      const p2 = element('section', 'projection-player p2');
      p2.append(element('strong', '', pairing.player2), element('small', '', 'Xanh · P2'), renderCounts(board, 2));
      sides.append(p1, p2);
      card.appendChild(sides);
      const boardSection = element('div', 'projection-board-wrap');
      boardSection.appendChild(element('div', `projection-turn ${game.live ? 'running' : ''}`, game.live ? 'Đang thi đấu' : 'Ván đã kết thúc'));
      const boardFrame = element('div', 'projection-board-frame');
      boardFrame.appendChild(renderBoard(board, lastMove));
      if (pairing.status === 'completed' && pairing.winner) {
        const winnerPlayer = pairing.winner_player === 1 ? 1 : 2;
        const victory = element('div', `projection-victory player-${winnerPlayer}`);
        victory.setAttribute('role', 'status');
        victory.append(
          element('strong', '', 'CHIẾN THẮNG CHUNG CUỘC'),
          element('span', '', `Player ${winnerPlayer}`),
          element('b', '', pairing.winner)
        );
        boardFrame.appendChild(victory);
      }
      boardSection.appendChild(boardFrame);
      card.appendChild(boardSection);
      const info = game.live
        ? `Đang trực tiếp · Đang xem lượt ${shown}/${game.turns}${lastMove ? ` · ${lastMove.san}` : ''}`
        : game.winner
          ? `Ván gần nhất: ${game.winner} thắng · ${shown}/${game.turns} lượt`
          : 'Đang chờ nước đi đầu tiên';
      card.appendChild(element('p', 'projection-note', info));
      const link = element('a', 'btn btn-sm', game.live ? 'Mở màn chiếu trận' : 'Xem ván gần nhất');
      link.href = `/replay/${game.match_id}`;
      card.appendChild(link);
    } else if (pairing.status === 'running') {
      card.appendChild(element('p', 'projection-note', 'Đang khởi chạy trận trên bàn chiếu...'));
    }

    if ((pairing.game_results || []).length) {
      const results = element('ol', 'projection-results');
      pairing.game_results.forEach((result) => {
        results.appendChild(
          element(
            'li',
            '',
            result.winner_username
              ? `Ván ${result.game_number}: ${result.winner_username} thắng`
              : `Ván ${result.game_number}: hòa`
          )
        );
      });
      card.appendChild(results);
    }
    if (pairing.winner) {
      card.appendChild(element('strong', 'projection-winner', `Thắng vòng: ${pairing.winner}`));
    }
    return card;
  }

  function paintPairings() {
    container.replaceChildren();
    if (!latestPairings.length) {
      container.appendChild(element('p', 'projection-note', 'Chưa có bracket nào được tạo.'));
      return;
    }
    latestPairings.forEach((pairing) => container.appendChild(renderPairing(pairing)));
  }

  async function queueNextRound() {
    if (roundRequestInFlight) return;
    roundRequestInFlight = true;
    if (startRoundButton) startRoundButton.disabled = true;
    if (controlMessage) controlMessage.textContent = 'Đang đưa vòng kế tiếp vào hàng chờ...';
    try {
      const response = await fetch('/api/admin/bracket/play', { method: 'POST' });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || 'Không thể bắt đầu vòng tiếp theo');
      if (controlMessage) controlMessage.textContent = `Đã bắt đầu ${data.round_name} trên ${data.concurrent_boards} bàn.`;
      await refresh();
    } catch (error) {
      if (controlMessage) controlMessage.textContent = error.message;
    } finally {
      roundRequestInFlight = false;
      if (startRoundButton) startRoundButton.disabled = false;
    }
  }

  function maybeAutoAdvance() {
    if (!autoAdvanceToggle || !autoAdvanceToggle.checked || roundRequestInFlight) return;
    if (latestPairings.some((pairing) => pairing.status === 'running')) return;
    const hasReadyPairing = latestPairings.some(
      (pairing) => pairing.status === 'pending' && pairing.player1 !== 'TBD' && pairing.player2 !== 'TBD'
    );
    if (hasReadyPairing) queueNextRound();
  }

  async function refresh() {
    try {
      const response = await fetch('/api/bracket/live', { cache: 'no-store' });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      latestPairings = data.pairings || [];
      latestPairings.forEach((pairing) => {
        if (!pairing.current_game) return;
        const oldGameId = displayedGameIds.get(pairing.id);
        if (oldGameId !== pairing.current_game.match_id) {
          displayedGameIds.set(pairing.id, pairing.current_game.match_id);
        }
        displayedTurns.set(
          pairing.id,
          Math.min(getSavedProgress(pairing.current_game.match_id), pairing.current_game.moves.length)
        );
      });
      paintPairings();
      maybeAutoAdvance();
    } catch (error) {
      container.replaceChildren(element('p', 'projection-note', `Không thể tải diễn biến: ${error.message}`));
    }
  }

  refresh();
  window.setInterval(refresh, 500);
  window.setInterval(() => {
    let advanced = false;
    latestPairings.forEach((pairing) => {
      const moveCount = pairing.current_game ? (pairing.current_game.moves || []).length : 0;
      const shown = displayedTurns.get(pairing.id) || 0;
      if (shown < moveCount) {
        const nextTurn = shown + 1;
        displayedTurns.set(pairing.id, nextTurn);
        if (pairing.current_game) {
          localStorage.setItem(progressKey(pairing.current_game.match_id), String(nextTurn));
        }
        advanced = true;
      }
    });
    if (advanced) paintPairings();
  }, 300);
})();
