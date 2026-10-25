// Lab page only: opens the sample dialogs with the question tone, plays
// each tone, clears the sample search and runs the progress bar again.
// Never used by the app.

import { play } from "../../../static/js/sound.js";

for (const button of document.querySelectorAll("[data-lab-open]")) {
  button.addEventListener("click", () => {
    play("prompt");
    document.getElementById(button.dataset.labOpen).showModal();
  });
}

for (const button of document.querySelectorAll("[data-lab-sound]")) {
  button.addEventListener("click", () => play(button.dataset.labSound));
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
