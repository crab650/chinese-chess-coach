(function () {
  "use strict";
  const form = document.getElementById("newGameForm");
  if (!form) return;
  const error = document.getElementById("formError");
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    error.hidden = true;
    try {
      const response = await fetch(form.dataset.api, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ human_side: form.elements.namedItem("human_side").value, level: form.elements.namedItem("level").value,
          coach_mode: form.elements.namedItem("coach_mode").value })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "無法開始對局");
      window.location.href = form.dataset.playTemplate.replace(/0$/, String(data.id));
    } catch (cause) {
      error.textContent = cause.message;
      error.hidden = false;
      button.disabled = false;
    }
  });
})();
