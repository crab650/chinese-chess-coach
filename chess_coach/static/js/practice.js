(function () {
  "use strict";
  const app = document.getElementById("practiceApp");
  if (!app) return;
  const board = document.getElementById("chessBoard");
  const title = document.getElementById("practiceTitle");
  const text = document.getElementById("practiceText");
  const error = document.getElementById("practiceError");
  let data = null;
  let selected = null;
  let answered = false;
  let busy = false;
  function showError(message) { error.textContent = message; error.hidden = !message; }
  function render(highlights = []) {
    if (!data) return;
    XQBoard.render(board, data.fen, { orientation: data.fen.split(" ")[1], legalMoves: answered ? [] : data.legal_moves,
      selected, highlights, onSquare });
  }
  async function onSquare(square) {
    if (!data || answered || busy) return;
    if (selected && data.legal_moves.includes(selected + square)) {
      busy = true; showError("");
      try {
        const response = await fetch(app.dataset.answerApi, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ move: selected + square }) });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || "無法檢查答案");
        answered = true; selected = null;
        title.textContent = result.correct ? "你找到了好走法！" : "再記住這個局面";
        text.textContent = result.correct ? `${result.played_description}。這一步可以。` : `${result.reason} 比較穩妥的是：${result.best_description}。`;
        document.getElementById("practiceStatus").textContent = result.correct ? "作答正確" : "看看建議走法";
        render([result.best_move.slice(0, 2), result.best_move.slice(2)]);
      } catch (cause) { showError(cause.message); }
      finally { busy = false; }
      return;
    }
    selected = data.legal_moves.some(move => move.startsWith(square)) ? square : null;
    render();
  }
  fetch(app.dataset.mistakeApi).then(response => response.json()).then(value => { data = value; render(); }).catch(cause => showError(cause.message));
})();
