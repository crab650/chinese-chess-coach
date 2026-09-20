(function () {
  "use strict";
  const NS = "http://www.w3.org/2000/svg";
  const FILES = "abcdefghi";
  const RED = { R: "俥", N: "傌", B: "相", A: "仕", K: "帥", C: "炮", P: "兵" };
  const BLACK = { r: "車", n: "馬", b: "象", a: "士", k: "將", c: "砲", p: "卒" };

  function svg(tag, attrs = {}, text = "") {
    const el = document.createElementNS(NS, tag);
    for (const [key, value] of Object.entries(attrs)) el.setAttribute(key, String(value));
    if (text) el.textContent = text;
    return el;
  }

  function parseFen(fen) {
    const rows = fen.split(" ")[0].split("/");
    return rows.map(row => {
      const squares = [];
      for (const char of row) {
        if (/^[1-9]$/.test(char)) squares.push(...Array(Number(char)).fill("."));
        else squares.push(char);
      }
      return squares;
    });
  }

  function coord(row, col) { return FILES[col] + String(9 - row); }
  function viewPosition(row, col, orientation) {
    const vr = orientation === "b" ? 9 - row : row;
    const vc = orientation === "b" ? 8 - col : col;
    return [50 + 55 * vc, 50 + 55 * vr];
  }
  function squarePosition(square, orientation) {
    const row = 9 - Number(square[1]);
    const col = FILES.indexOf(square[0]);
    return viewPosition(row, col, orientation);
  }

  function drawGrid(root) {
    root.appendChild(svg("rect", { x: 14, y: 14, width: 512, height: 572, rx: 13, class: "board-surface" }));
    root.appendChild(svg("rect", { x: 28, y: 28, width: 484, height: 544, rx: 3, class: "board-border" }));
    for (let row = 0; row < 10; row++) {
      const y = 50 + 55 * row;
      root.appendChild(svg("line", { x1: 50, y1: y, x2: 490, y2: y, class: "board-line" }));
    }
    for (let col = 0; col < 9; col++) {
      const x = 50 + 55 * col;
      if (col === 0 || col === 8) root.appendChild(svg("line", { x1: x, y1: 50, x2: x, y2: 545, class: "board-line" }));
      else {
        root.appendChild(svg("line", { x1: x, y1: 50, x2: x, y2: 270, class: "board-line" }));
        root.appendChild(svg("line", { x1: x, y1: 325, x2: x, y2: 545, class: "board-line" }));
      }
    }
    for (const [a, b, c, d] of [[215, 50, 325, 160], [325, 50, 215, 160], [215, 435, 325, 545], [325, 435, 215, 545]]) {
      root.appendChild(svg("line", { x1: a, y1: b, x2: c, y2: d, class: "board-line" }));
    }
    root.appendChild(svg("text", { x: 160, y: 308, class: "river-text", "text-anchor": "middle" }, "楚 河"));
    root.appendChild(svg("text", { x: 380, y: 308, class: "river-text", "text-anchor": "middle" }, "漢 界"));
  }

  function render(root, fen, options = {}) {
    const orientation = options.orientation || "w";
    const rows = parseFen(fen);
    const legalMoves = options.legalMoves || [];
    const selected = options.selected;
    const highlights = options.highlights || [];
    const lastMove = options.lastMove;
    root.replaceChildren();
    drawGrid(root);
    const marks = svg("g");
    const pieces = svg("g");
    const hitboxes = svg("g");
    root.append(marks, pieces, hitboxes);

    if (options.threatMove) {
      const [fromX, fromY] = squarePosition(options.threatMove.slice(0, 2), orientation);
      const [toX, toY] = squarePosition(options.threatMove.slice(2), orientation);
      if (options.threatStraight) marks.appendChild(svg("line", { x1: fromX, y1: fromY, x2: toX, y2: toY, class: "threat-line" }));
      marks.appendChild(svg("circle", { cx: fromX, cy: fromY, r: 32, class: "threat-ring" }));
    }

    for (const square of options.responsePieces || []) {
      const [x, y] = squarePosition(square, orientation);
      marks.appendChild(svg("circle", { cx: x, cy: y, r: 30, class: "response-ring" }));
    }

    for (const square of lastMove ? [lastMove.slice(0, 2), lastMove.slice(2, 4)] : []) {
      const [x, y] = squarePosition(square, orientation);
      marks.appendChild(svg("circle", { cx: x, cy: y, r: 29, class: "last-move-ring" }));
    }
    for (const square of highlights) {
      const [x, y] = squarePosition(square, orientation);
      marks.appendChild(svg("circle", { cx: x, cy: y, r: 30, class: "hint-ring" }));
    }
    if (options.recommendation) {
      const [fromX, fromY] = squarePosition(options.recommendation.slice(0, 2), orientation);
      const [toX, toY] = squarePosition(options.recommendation.slice(2), orientation);
      marks.appendChild(svg("circle", { cx: fromX, cy: fromY, r: 30, class: "guide-from-ring" }));
      marks.appendChild(svg("circle", { cx: toX, cy: toY, r: 30, class: "guide-to-ring" }));
    }
    if (options.checkedKing) {
      const [x, y] = squarePosition(options.checkedKing, orientation);
      marks.appendChild(svg("circle", { cx: x, cy: y, r: 30, class: "check-ring" }));
    }
    if (selected) {
      const [x, y] = squarePosition(selected, orientation);
      marks.appendChild(svg("circle", { cx: x, cy: y, r: 29, class: "selected-ring" }));
      for (const move of legalMoves.filter(value => value.startsWith(selected))) {
        const [tx, ty] = squarePosition(move.slice(2), orientation);
        marks.appendChild(svg("circle", { cx: tx, cy: ty, r: 7, class: "legal-dot" }));
      }
    }
    for (let row = 0; row < 10; row++) {
      for (let col = 0; col < 9; col++) {
        const [x, y] = viewPosition(row, col, orientation);
        const square = coord(row, col);
        const piece = rows[row][col];
        if (piece !== ".") {
          const group = svg("g", { class: `piece ${piece === piece.toUpperCase() ? "red" : "black"}` });
          group.appendChild(svg("circle", { cx: x, cy: y, r: 25, class: "piece-shadow" }));
          group.appendChild(svg("circle", { cx: x, cy: y, r: 23, class: "piece-disc" }));
          group.appendChild(svg("circle", { cx: x, cy: y, r: 18, class: "piece-inner" }));
          group.appendChild(svg("text", { x, y: y + 8, "text-anchor": "middle", class: "piece-label" }, RED[piece] || BLACK[piece] || piece));
          pieces.appendChild(group);
        }
        hitboxes.appendChild(svg("circle", { cx: x, cy: y, r: 26, fill: "transparent", class: "hitbox", "data-square": square }));
      }
    }
    root.onclick = event => {
      const target = event.target.closest("[data-square]");
      if (target && options.onSquare) options.onSquare(target.dataset.square);
    };
  }

  window.XQBoard = { render, parseFen };
})();
