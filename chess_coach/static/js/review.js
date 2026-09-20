(function () {
  "use strict";
  const app = document.getElementById("reviewApp");
  if (!app) return;
  const game = JSON.parse(app.dataset.game);
  const mistakes = JSON.parse(app.dataset.mistakes);
  const history = game.history;
  const board = document.getElementById("chessBoard");
  const title = document.getElementById("reviewMoveTitle");
  const text = document.getElementById("reviewMoveText");
  const position = document.getElementById("reviewPosition");
  const list = document.getElementById("moveList");
  let index = 0;
  history.forEach((item, number) => {
    const li = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button"; button.textContent = `${number + 1}. ${item.label}`;
    button.addEventListener("click", () => { index = number + 1; render(); });
    li.append(button); list.append(li);
  });
  function render() {
    const fen = index < history.length ? history[index].fen_before : game.fen;
    XQBoard.render(board, fen, { orientation: game.human_side, lastMove: index ? history[index - 1].move : null });
    position.textContent = index ? `第 ${index} 步之後` : "開局";
    title.textContent = index ? `${index}. ${history[index - 1].label}` : "開局局面";
    const mistake = mistakes.find(item => item.ply === index);
    text.textContent = mistake ? `${mistake.reason} 當時較穩妥的是：${mistake.best}。` : index ? (history[index - 1].actor === "human" ? "這是你當時選擇的走法。" : "這是電腦的回應。") : "按「下一步」開始複盤。";
    document.getElementById("firstMove").disabled = index === 0;
    document.getElementById("prevMove").disabled = index === 0;
    document.getElementById("nextMove").disabled = index === history.length;
    [...list.querySelectorAll("button")].forEach((button, number) => button.classList.toggle("active", number === index - 1));
  }
  document.getElementById("firstMove").onclick = () => { index = 0; render(); };
  document.getElementById("prevMove").onclick = () => { index = Math.max(0, index - 1); render(); };
  document.getElementById("nextMove").onclick = () => { index = Math.min(history.length, index + 1); render(); };
  render();
})();
