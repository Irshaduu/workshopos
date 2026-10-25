// Lab page only: opens the sample dialogs, clears the sample search and
// runs the progress bar again. Never used by the app.

for (const button of document.querySelectorAll("[data-lab-open]")) {
  button.addEventListener("click", () => {
    document.getElementById(button.dataset.labOpen).showModal();
  });
}

for (const clear of document.querySelectorAll(".search__clear")) {
  clear.addEventListener("click", () => {
    const input = clear.form.elements.q;
    input.value = "";
    input.focus();
  });
}

for (const button of document.querySelectorAll("[data-lab-replay]")) {
  button.addEventListener("click", () => {
    const bar = document.getElementById(button.dataset.labReplay);
    bar.replaceWith(bar.cloneNode());
  });
}
