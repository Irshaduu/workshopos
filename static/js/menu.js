// The app's menu (ROLE-33, ROLE-34): a modal dialog, so the keyboard stays
// inside it, Escape closes it, and a screen reader knows it is a dialog. The
// tab bar's last tab opens it; its close button, or a tap on the shaded page
// beside it, closes it. It only shows: the server decides what is in it.

import { readEnabled, setEnabled } from "./sound.js";

const menu = document.getElementById("app-menu");
const opener = document.querySelector('[aria-controls="app-menu"]');

opener.addEventListener("click", () => {
  menu.showModal();
  opener.setAttribute("aria-expanded", "true");
});

menu.addEventListener("close", () => {
  opener.setAttribute("aria-expanded", "false");
});

menu.querySelector("[data-menu-close]").addEventListener("click", () => {
  menu.close();
});

// The dialog fills its own box with its head and body, so a tap whose target
// is the dialog itself landed on the backdrop.
menu.addEventListener("click", (event) => {
  if (event.target === menu) {
    menu.close();
  }
});

// Sounds on or off, for this device only: the Floor tablet and an owner's
// phone want different answers. The server sends both words, and app.css
// shows the one that matches the switch.
const sounds = menu.querySelector("[data-menu-sounds]");

sounds.setAttribute("aria-checked", String(readEnabled()));

sounds.addEventListener("click", () => {
  const on = sounds.getAttribute("aria-checked") !== "true";
  setEnabled(on);
  sounds.setAttribute("aria-checked", String(on));
});
