// The Staff list's row buttons (STAFF-22). It only shows: the server decides everything.

function setOpen(toggle, open) {
  const actions = document.getElementById(toggle.getAttribute("aria-controls"));
  toggle.setAttribute("aria-expanded", String(open));
  actions.hidden = !open;
  // In a long card, the row may open below the part of the card that shows.
  if (open) {
    actions.scrollIntoView({ block: "nearest" });
  }
}

document.addEventListener("click", (event) => {
  // One row open at a time, and a tap anywhere else closes it (v1). A tap on a row's
  // buttons or in its card leaves it open, so the keyboard comes back to Edit when the
  // card closes.
  const toggle = event.target.closest("[data-row-more]");
  if (!event.target.closest(".staff-row__actions, dialog")) {
    for (const open of document.querySelectorAll('[data-row-more][aria-expanded="true"]')) {
      if (open !== toggle) {
        setOpen(open, false);
      }
    }
  }
  if (toggle) {
    setOpen(toggle, toggle.getAttribute("aria-expanded") !== "true");
  }
});
