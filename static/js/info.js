// The info button (docs/DESIGN.md, Help notes): a tap shows or hides the
// "how it works" note it controls. One listener on the page covers every
// info button, including ones that arrive later in a page update.

document.addEventListener("click", (event) => {
  const button = event.target.closest(".info[aria-controls]");
  if (!button) {
    return;
  }
  const note = document.getElementById(button.getAttribute("aria-controls"));
  if (!note) {
    return;
  }
  const open = button.getAttribute("aria-expanded") !== "true";
  button.setAttribute("aria-expanded", String(open));
  note.hidden = !open;
});
