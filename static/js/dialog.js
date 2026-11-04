// Every card over the page, for every page of the app: a button with
// data-dialog-open="its id" opens it as a modal dialog, so the keyboard stays inside
// it and Escape closes it. A button with data-dialog-close inside it closes it, and so
// does a tap on the shaded page beside it. A dialog sent with data-open-now opens when
// the page does, like a refused form's card. It only shows: the server decides.

// Whether a click on the dialog itself landed outside its box, on the shaded page. A
// click on the box's own padding has the dialog as its target too, and must not close
// a card someone is typing in.
function onTheShade(dialog, event) {
  const box = dialog.getBoundingClientRect();
  return (
    event.clientX < box.left ||
    event.clientX > box.right ||
    event.clientY < box.top ||
    event.clientY > box.bottom
  );
}

document.addEventListener("click", (event) => {
  const opener = event.target.closest("[data-dialog-open]");
  if (opener) {
    document.getElementById(opener.dataset.dialogOpen).showModal();
  }
  if (event.target.closest("[data-dialog-close]")) {
    event.target.closest("dialog").close();
  }
  if (event.target.matches("dialog") && onTheShade(event.target, event)) {
    event.target.close();
  }
});

document.querySelector("dialog[data-open-now]")?.showModal();
