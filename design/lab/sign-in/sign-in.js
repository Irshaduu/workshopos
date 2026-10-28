// Lab page only: shows one sign-in state at a time, picked with the
// switch or the address (index.html#locked), and walks the steps with
// fake answers. In the app the server decides every step (ADR-0025); this
// file only stands in for it. Never used by the app.

const states = [...document.querySelectorAll("[data-state]")];
const names = new Set(states.map((state) => state.dataset.state));
let codeAskedAt = 0;

function show(name) {
  const shown = names.has(name) ? name : "start";
  for (const state of states) {
    state.hidden = state.dataset.state !== shown;
  }
  for (const radio of document.querySelectorAll('input[name="lab-state"]')) {
    radio.checked = radio.value === shown;
  }
  if (location.hash !== `#${shown}`) {
    history.replaceState(null, "", `#${shown}`);
  }
}

function fill(selector, text) {
  for (const element of document.querySelectorAll(selector)) {
    element.textContent = text;
  }
}

// What the server would answer after each form, with fake data.
const answer = {
  start(form) {
    const typed = form.elements.who.value.trim();
    if (typed.includes("@")) {
      fill("[data-lab-email]", typed);
      codeAskedAt = Date.now();
      return "code";
    }
    fill("[data-lab-username]", typed);
    return "password";
  },
  code: () => "code-wrong",
  password: () => "password-wrong",
  resend() {
    if (Date.now() - codeAskedAt < 60_000) {
      return "code-wait";
    }
    codeAskedAt = Date.now();
    return "code";
  },
};

for (const form of document.querySelectorAll("form[data-lab-step]")) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    const button = form.querySelector('[type="submit"]');
    // Busy after the first tap; a second tap sends nothing (SIGN-14).
    if (button.getAttribute("aria-busy") === "true") {
      return;
    }
    button.setAttribute("aria-busy", "true");
    setTimeout(() => {
      button.removeAttribute("aria-busy");
      show(answer[form.dataset.labStep](form));
    }, 700);
  });
}

for (const radio of document.querySelectorAll('input[name="lab-state"]')) {
  radio.addEventListener("change", () => show(radio.value));
}

window.addEventListener("hashchange", () => show(location.hash.slice(1)));
show(location.hash.slice(1));
