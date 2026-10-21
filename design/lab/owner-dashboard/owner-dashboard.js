// Owner dashboard lab only, never used by the app. Tapping a check's name
// opens its Where, Why and How below it; tapping again closes it. It only
// shows and hides: the checks themselves come from the server.
(function () {
  "use strict";

  document.addEventListener("click", function (event) {
    var name = event.target.closest(".od1-checks__name");
    if (!name) { return; }
    var panel = document.getElementById(name.getAttribute("aria-controls"));
    var open = name.getAttribute("aria-expanded") !== "true";
    name.setAttribute("aria-expanded", String(open));
    panel.hidden = !open;
  });
})();
