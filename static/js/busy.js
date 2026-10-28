// The busy button (docs/DESIGN.md, Loading): after the first tap, the
// button shows it is busy, and a second tap or Enter sends nothing, so a
// double tap never sends a form twice (SIGN-14). It only shows that the
// first tap is on its way: the server still refuses a double save
// (docs/PLAN.md, Phase 5).
//
// Two marks. data-sending on the form is the guard: a second submit stops,
// whichever button or key sent it. aria-busy on the tapped button is what
// people see (components.css shows the spinner) and what a screen reader
// hears. The button is never disabled: a disabled button's name and value
// are left out of what the form sends, and v1 found that disabling it does
// not stop an Enter already on its way.

// Whether this submit may go. The first one may: the form is marked as
// sending, and the tapped button as busy. Every later one stops.
export function claim(form, button) {
  if ("sending" in form.dataset) {
    return false;
  }
  form.dataset.sending = "true";
  button?.setAttribute("aria-busy", "true");
  return true;
}

// Frees every form on the page again. For a page the browser shows from
// its memory after Back: the marks from before would stop its forms for
// good.
export function release(root) {
  for (const form of root.querySelectorAll("form[data-sending]")) {
    delete form.dataset.sending;
    for (const button of form.querySelectorAll('[aria-busy="true"]')) {
      button.removeAttribute("aria-busy");
    }
  }
}

// Everything below needs a browser.

if (typeof document !== "undefined") {
  document.addEventListener("submit", (event) => {
    // A submit the page's own code already stopped is left alone.
    if (event.defaultPrevented) {
      return;
    }
    if (!claim(event.target, event.submitter)) {
      event.preventDefault();
    }
  });

  window.addEventListener("pageshow", (event) => {
    if (event.persisted) {
      release(document);
    }
  });
}
