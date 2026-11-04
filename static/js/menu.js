// The app's menu (ROLE-33, ROLE-34): a modal dialog, opened by the tab bar's last
// tab and closed by its close button or a tap beside it (static/js/dialog.js). Here:
// what only the menu does. It only shows: the server decides what is in it.

import { readEnabled, setEnabled } from "./sound.js";

const menu = document.getElementById("app-menu");
const opener = document.querySelector('[aria-controls="app-menu"]');

opener.addEventListener("click", () => {
  opener.setAttribute("aria-expanded", "true");
});

menu.addEventListener("close", () => {
  opener.setAttribute("aria-expanded", "false");
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
