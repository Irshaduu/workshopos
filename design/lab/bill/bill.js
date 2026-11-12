// Bill lab only, never used by the app. v1's fitSheet: the bill keeps its A4
// width, and a narrow screen scales the whole sheet down, so what an owner
// reads on a phone is the bill that prints. It only shows; it works out no
// money.
(function () {
  "use strict";

  var wrap = document.querySelector(".sheet-wrap");
  var sheet = document.querySelector(".sheet");

  function fit() {
    if (!wrap || !sheet) {
      return;
    }
    sheet.style.transform = "";
    wrap.style.height = "";
    var available = wrap.clientWidth;
    var natural = sheet.offsetWidth;
    if (!natural || available <= 0 || available >= natural) {
      return;
    }
    var scale = available / natural;
    sheet.style.transform = "scale(" + scale + ")";
    wrap.style.height = sheet.offsetHeight * scale + "px";
  }

  fit();
  window.addEventListener("resize", fit);
  // A state with more rows makes the sheet taller, so fit it again.
  document.addEventListener("change", fit);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(fit);
  }
}());
