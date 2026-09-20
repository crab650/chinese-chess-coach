(function () {
  "use strict";
  const app = document.getElementById("playApp");
  if (!app) return;
  const board = document.getElementById("chessBoard");
  const coachTitle = document.getElementById("coachTitle");
  const coachText = document.getElementById("coachText");
  const coachActions = document.getElementById("coachActions");
  const coachError = document.getElementById("coachError");
  const turnStatus = document.getElementById("turnStatus");
  const sideLabel = document.getElementById("sideLabel");
  const boardNotice = document.getElementById("boardNotice");
  const pendingBoardActions = document.getElementById("pendingBoardActions");
  const moveList = document.getElementById("moveList");
  const moreHint = document.getElementById("moreHint");
  const retryMove = document.getElementById("retryMove");
  const acceptMove = document.getElementById("acceptMove");
  const modeToggle = document.getElementById("modeToggle");
  const guideTitle = document.getElementById("guideTitle");
  const guideProblem = document.getElementById("guideProblem");
  const guideReason = document.getElementById("guideReason");
  const guideError = document.getElementById("guideError");
  const previewGuide = document.getElementById("previewGuide");
  const compareGuide = document.getElementById("compareGuide");
  const cancelCompare = document.getElementById("cancelCompare");
  const retryGuide = document.getElementById("retryGuide");
  const variationPanel = document.getElementById("variationPanel");
  const variationBoard = document.getElementById("variationBoard");
  const opponentPanel = document.getElementById("opponentLesson");
  const opponentMove = document.getElementById("opponentMove");
  const opponentQuestion = document.getElementById("opponentQuestion");
  const opponentChoices = document.getElementById("opponentChoices");
  const opponentResult = document.getElementById("opponentResult");
  const opponentContinue = document.getElementById("opponentContinue");
  const opponentError = document.getElementById("opponentError");
  let game = null;
  let guide = null;
  let comparison = null;
  let comparing = false;
  let variationBranch = "recommended";
  let guideLoading = false;
  let guideRequestId = 0;
  let variationIndex = 0;
  let selected = null;
  let hintLevel = 0;
  let busy = false;
  let lessonDismissedPly = null;

  async function post(url, body = {}) {
    const response = await fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "操作失敗");
    return data;
  }
  function showError(message) { coachError.textContent = message; coachError.hidden = !message; }
  function lessonOpen() { return !!(game?.opponent_lesson && lessonDismissedPly !== game.opponent_lesson.ply); }
  function canGuide() { return game && game.coach_mode === "guided" && game.status === "playing" && !game.pending && !lessonOpen(); }
  function clearGuide() { guideRequestId++; guide = null; comparison = null; comparing = false; guideLoading = false; guideError.hidden = true; opponentError.hidden = true; variationPanel.hidden = true; }
  function renderOpponentLesson() {
    const lesson = lessonOpen() ? game.opponent_lesson : null;
    opponentPanel.hidden = !lesson;
    if (!lesson) return;
    opponentMove.textContent = `電腦剛走：${lesson.move_label}`;
    opponentQuestion.textContent = lesson.question;
    opponentChoices.replaceChildren();
    opponentResult.hidden = !lesson.answered;
    opponentContinue.hidden = !lesson.answered;
    if (lesson.answered) {
      opponentResult.textContent = `${lesson.correct ? "你看對了！" : lesson.choice === "unsure" ? "一起看答案：" : "再看一次："}這步是「${lesson.answer}」。${lesson.explanation}`;
    } else {
      for (const choice of ["check", "capture", "quiet", "unsure"]) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "button button-secondary";
        button.textContent = lesson.options[choice];
        button.addEventListener("click", () => answerOpponentLesson(choice));
        opponentChoices.append(button);
      }
    }
  }
  async function answerOpponentLesson(choice) {
    if (busy || !lessonOpen() || game.opponent_lesson.answered) return;
    busy = true; opponentError.hidden = true;
    try { game = await post(app.dataset.opponentLessonApi, { ply: game.opponent_lesson.ply, choice }); }
    catch (cause) { opponentError.textContent = cause.message; opponentError.hidden = false; }
    finally { busy = false; render(); }
  }
  function renderGuide() {
    modeToggle.textContent = game.coach_mode === "guided" ? "改自主練習" : "啟用大師帶走";
    previewGuide.hidden = true;
    compareGuide.hidden = true;
    cancelCompare.hidden = !comparing;
    retryGuide.hidden = true;
    guideProblem.hidden = true;
    if (game.coach_mode !== "guided") {
      guideTitle.textContent = "想知道下一步怎麼走？";
      guideReason.textContent = "切換後，每回合都會先給建議、原因與可播放的後續推演。";
    } else if (game.pending) {
      guideTitle.textContent = "先處理剛才這一步";
      guideReason.textContent = "選擇重走或保留原走法後，我會分析下一個局面。";
    } else if (lessonOpen()) {
      guideTitle.textContent = "先看對方剛才的走法";
      guideReason.textContent = "猜完並看過棋盤依據後，再看我方下一步建議。你也可以直接走棋跳過這題。";
    } else if (game.status !== "playing") {
      guideTitle.textContent = "這盤棋已結束";
      guideReason.textContent = "可以到對局紀錄回看每一步。";
    } else if (guideLoading) {
      guideTitle.textContent = "正在推演下一步…";
      guideReason.textContent = "正在確認建議和後續走法。";
    } else if (guide && guide.fen === game.fen) {
      guideTitle.textContent = comparing ? "選一個你想比較的合法走法" : `建議：${guide.best_label}`;
      guideProblem.textContent = guide.focus.problem;
      guideProblem.hidden = false;
      guideReason.textContent = comparing ? "在棋盤點選棋子和落點。我會先比較兩條後續，這一步不會下到對局。" : guide.reason.slice(guide.focus.problem.length);
      previewGuide.hidden = comparing;
      compareGuide.hidden = comparing;
    } else {
      guideTitle.textContent = "等待分析";
      guideReason.textContent = "按重新分析取得這個局面的建議。";
      retryGuide.hidden = false;
    }
  }
  async function loadGuide() {
    if (!canGuide()) return;
    const requestId = ++guideRequestId;
    const fen = game.fen;
    guide = null; guideLoading = true; guideError.hidden = true; render();
    try {
      const response = await fetch(app.dataset.guideApi);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "無法取得建議");
      if (requestId === guideRequestId && game.fen === fen && canGuide()) guide = data;
    } catch (cause) {
      if (requestId === guideRequestId) { guideError.textContent = cause.message; guideError.hidden = false; }
    } finally {
      if (requestId === guideRequestId) { guideLoading = false; render(); }
    }
  }
  function renderVariation() {
    const variation = comparison ? comparison[variationBranch] : guide;
    if (!variation) return;
    const step = variationIndex ? variation.line[variationIndex - 1] : null;
    XQBoard.render(variationBoard, step ? step.fen : variation.fen,
      { orientation: game.human_side, lastMove: step?.move, recommendation: step ? null : variation.best_move,
        threatMove: step ? null : variation.focus.threat_move,
        threatStraight: variation.focus.threat_straight });
    document.getElementById("variationStep").textContent = variationIndex ? `推演第 ${variationIndex} 步 / 共 ${variation.line.length} 步` : "現在局面";
    document.getElementById("variationMove").textContent = step ? `${step.actor === "human" ? "我方" : "對方"}：${step.label}` : `建議：${variation.best_label}`;
    document.getElementById("variationExplanation").textContent = step ? step.explanation + (variationIndex === 1 && variation.line.length > 1 ? " 先猜猜對方會怎麼下，再按下一步。" : "") : variation.reason;
    document.getElementById("prevVariation").disabled = variationIndex === 0;
    document.getElementById("nextVariation").disabled = variationIndex >= variation.line.length;
    document.getElementById("variationTitle").textContent = comparison ? "比較兩種走法" : "看看後面可能怎麼走";
    document.getElementById("comparisonSummary").hidden = !comparison;
    document.getElementById("comparisonSummary").textContent = comparison?.summary || "";
    document.getElementById("branchTabs").hidden = !comparison;
    document.getElementById("branchRecommended").classList.toggle("active", variationBranch === "recommended");
    document.getElementById("branchAlternative").classList.toggle("active", variationBranch === "alternative");
  }
  function ownPieceAt(square) {
    const rows = XQBoard.parseFen(game.fen);
    const piece = rows[9 - Number(square[1])]["abcdefghi".indexOf(square[0])];
    return piece !== "." && (game.human_side === "w" ? piece === piece.toUpperCase() : piece === piece.toLowerCase());
  }
  function render() {
    if (!game) return;
    const pending = game.pending;
    const revealedLesson = lessonOpen() && game.opponent_lesson.answered ? game.opponent_lesson : null;
    const fen = pending && hintLevel === 2 ? game.fen : game.display_fen;
    const highlights = pending ? (hintLevel === 2 ? [pending.best_move.slice(0, 2), pending.best_move.slice(2)] : hintLevel === 1 ? pending.highlights : []) : revealedLesson ? revealedLesson.highlights : [];
    const responsePieces = game.in_check && !pending ? [...new Set(game.legal_moves.map(move => move.slice(0, 2)))] : [];
    XQBoard.render(board, fen, { orientation: game.human_side, legalMoves: game.legal_moves,
      selected, highlights, checkedKing: pending ? null : game.checked_king,
      responsePieces, recommendation: canGuide() && guide?.fen === game.fen ? guide.best_move : null,
      threatMove: revealedLesson?.threat_move || (canGuide() && guide?.fen === game.fen ? guide.focus.threat_move : null),
      threatStraight: revealedLesson?.threat_straight || guide?.focus.threat_straight,
      lastMove: pending ? pending.played_move : game.history.at(-1)?.move, onSquare });
    sideLabel.textContent = `你執${game.human_side === "w" ? "紅" : "黑"}方 · ${ { beginner: "入門", normal: "普通", challenge: "挑戰" }[game.level] }`;
    turnStatus.textContent = pending ? "教練暫停對局：請先選重走或保留" : game.status === "won" ? "你贏了這盤棋" : game.status === "lost" ? "這盤棋已結束" : comparing ? "比較模式：選一個想走的合法步" : lessonOpen() ? "先猜電腦這步的效果，也可直接走棋" : game.in_check ? "你正被將軍，請先應將" : "輪到你走棋";
    const hasMove = selected && game.legal_moves.some(move => move.startsWith(selected));
    boardNotice.textContent = pending ? "按下方按鈕才能繼續" : comparing ? "比較不會改動棋局" : revealedLesson ? "紅色標示電腦這步的效果" : lessonOpen() ? "仍可直接走棋跳過本題" : !selected ? "" : hasMove ? "綠點是這顆棋子的合法落點" : game.in_check ? "這顆棋子目前不能解將，請選綠圈棋子" : "這顆棋子目前沒有合法走法";
    pendingBoardActions.hidden = !pending;
    coachActions.hidden = !pending;
    if (pending) {
      coachTitle.textContent = "先決定怎麼處理這一步";
      coachText.textContent = `${pending.hints[hintLevel]} 想好後，請選「重走這一步」或「保留這步繼續」。`;
      moreHint.hidden = hintLevel >= 2;
    } else if (game.status === "won") {
      coachTitle.textContent = "下得好！";
      coachText.textContent = "這盤棋已結束。回看關鍵局面，記住你找到的好走法。";
    } else if (game.status === "lost") {
      coachTitle.textContent = "再從這盤棋學一點";
      coachText.textContent = "到對局紀錄回看走法，或練習剛才收錄的錯題。";
    } else {
      coachTitle.textContent = "先觀察，再落子";
      coachText.textContent = lessonOpen() && !game.opponent_lesson.answered ? "先觀察電腦剛走的位置，試著回答上方問題。仍可直接走棋。" : game.in_check ? "對方正在將軍。綠圈標出可以應將的棋子；點選其中一顆，綠點會顯示合法落點。" : "看看對方的威脅，再選你想走的一步。遇到明顯失誤時，我會陪你重看。";
    }
    renderOpponentLesson();
    renderGuide();
    moveList.replaceChildren();
    if (!game.history.length) {
      const empty = document.createElement("li"); empty.className = "empty-state"; empty.textContent = "還沒有走棋。"; moveList.append(empty);
    } else {
      game.history.forEach((item, index) => {
        const li = document.createElement("li");
        li.innerHTML = `<span class="move-number">${index + 1}.</span><span></span>`;
        li.lastElementChild.textContent = item.label;
        moveList.append(li);
      });
      moveList.scrollTop = moveList.scrollHeight;
    }
  }
  async function onSquare(square) {
    if (busy || !game || game.status !== "playing") return;
    if (game.pending) { boardNotice.textContent = "教練正在等你選重走或保留這步"; return; }
    if (selected && game.legal_moves.includes(selected + square)) {
      if (comparing) {
        busy = true; guideError.hidden = true; turnStatus.textContent = "正在比較兩種走法…";
        try {
          const result = await post(app.dataset.compareApi, { move: selected + square, fen: game.fen });
          if (result.fen !== game.fen) throw new Error("棋局已更新，請重新整理");
          comparison = result; comparing = false; selected = null;
          variationBranch = "alternative"; variationIndex = 0;
          variationPanel.hidden = false; renderVariation();
          document.getElementById("closeVariation").focus();
        } catch (cause) { guideError.textContent = cause.message; guideError.hidden = false; }
        finally { busy = false; render(); }
        return;
      }
      busy = true; showError(""); turnStatus.textContent = "教練正在看這一步…";
      try { game = await post(app.dataset.moveApi, { move: selected + square }); clearGuide(); selected = null; hintLevel = 0; }
      catch (cause) { showError(cause.message); }
      finally { busy = false; render(); if (canGuide() && !guide) loadGuide(); }
      return;
    }
    selected = ownPieceAt(square) ? square : null;
    render();
  }
  async function action(url) {
    if (busy) return;
    busy = true; showError("");
    try { game = await post(url); clearGuide(); selected = null; hintLevel = 0; }
    catch (cause) { showError(cause.message); }
    finally { busy = false; render(); if (canGuide() && !guide) loadGuide(); }
  }
  modeToggle.addEventListener("click", async () => {
    if (busy || !game) return;
    busy = true; showError("");
    try {
      const mode = game.coach_mode === "guided" ? "independent" : "guided";
      game = await post(app.dataset.modeApi, { coach_mode: mode });
      clearGuide(); render();
    } catch (cause) { showError(cause.message); }
    finally { busy = false; if (canGuide()) loadGuide(); }
  });
  previewGuide.addEventListener("click", () => {
    if (!guide || guide.fen !== game.fen) return;
    comparison = null; variationBranch = "recommended"; variationIndex = 0; variationPanel.hidden = false; renderVariation();
    document.getElementById("closeVariation").focus();
  });
  compareGuide.addEventListener("click", () => {
    if (!guide || !canGuide() || busy) return;
    comparing = true; selected = null; guideError.hidden = true; render();
  });
  cancelCompare.addEventListener("click", () => { comparing = false; selected = null; render(); });
  document.getElementById("branchRecommended").addEventListener("click", () => { variationBranch = "recommended"; variationIndex = 0; renderVariation(); });
  document.getElementById("branchAlternative").addEventListener("click", () => { variationBranch = "alternative"; variationIndex = 0; renderVariation(); });
  retryGuide.addEventListener("click", loadGuide);
  opponentContinue.addEventListener("click", () => {
    if (!lessonOpen() || !game.opponent_lesson.answered) return;
    lessonDismissedPly = game.opponent_lesson.ply;
    render();
    if (canGuide()) loadGuide();
  });
  document.getElementById("closeVariation").addEventListener("click", () => { variationPanel.hidden = true; previewGuide.focus(); });
  document.getElementById("prevVariation").addEventListener("click", () => { variationIndex = Math.max(0, variationIndex - 1); renderVariation(); });
  document.getElementById("nextVariation").addEventListener("click", () => { const line = comparison ? comparison[variationBranch].line : guide.line; variationIndex = Math.min(line.length, variationIndex + 1); renderVariation(); });
  document.addEventListener("keydown", event => { if (event.key === "Escape" && !variationPanel.hidden) variationPanel.hidden = true; });
  moreHint.addEventListener("click", () => { hintLevel = Math.min(2, hintLevel + 1); render(); });
  retryMove.addEventListener("click", () => action(app.dataset.retryApi));
  acceptMove.addEventListener("click", () => action(app.dataset.acceptApi));
  document.getElementById("boardRetryMove").addEventListener("click", () => action(app.dataset.retryApi));
  document.getElementById("boardAcceptMove").addEventListener("click", () => action(app.dataset.acceptApi));
  fetch(app.dataset.gameApi).then(response => response.json()).then(data => { game = data; render(); if (canGuide()) loadGuide(); }).catch(cause => showError(cause.message));
})();
