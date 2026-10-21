// Job card lab only, never used by the app. v1's Old Bills method: each
// list keeps one open, empty row at its end, and typing into it opens the
// next one, so there are no Add buttons. The row numbers and the editing
// name tags follow along.
(function () {
  "use strict";

  function rowsOf(list) {
    return Array.from(list.children).filter(function (el) {
      return el.matches("tr, .jc1-row");
    });
  }

  // Typed means a box with something in it, or a shop chosen. The status
  // does not count: it always holds a value (v1's rule), so it would make
  // every untouched row look filled in.
  function hasContent(row) {
    var boxes = Array.from(row.querySelectorAll("input"));
    var shops = Array.from(row.querySelectorAll("select:not(.jc1-status)"));
    return boxes.some(function (box) { return box.value.trim() !== ""; }) ||
      shops.some(function (box) { return box.value !== ""; });
  }

  function renumber(list) {
    rowsOf(list).forEach(function (row, i) {
      var cell = row.querySelector(".jc1-idx");
      if (!cell) { return; }
      var number = Array.from(cell.childNodes).find(function (node) {
        return node.nodeType === Node.TEXT_NODE;
      });
      if (!number) {
        number = document.createTextNode("");
        cell.prepend(number);
      }
      number.nodeValue = String(i + 1);
      var tag = cell.querySelector(".jc1-rowtag");
      var name = row.querySelector("input");
      if (tag) {
        tag.textContent = (i + 1) + ". " + ((name && name.value.trim()) || list.dataset.new);
      }
    });
  }

  // A status box takes its colour the moment it changes, not after saving
  // (v1 does the same): red not started, amber working or ordered, green
  // fixed or received.
  var TONE = {
    pending: "is-pending", working: "is-working", ordered: "is-working",
    fixed: "is-fixed", received: "is-fixed"
  };
  document.addEventListener("change", function (event) {
    var box = event.target;
    if (!box.matches || !box.matches("select.jc1-status")) { return; }
    box.classList.remove("is-pending", "is-working", "is-fixed");
    box.classList.add(TONE[box.value.trim().toLowerCase()] || "is-pending");
  });

  // The VIN's meter: one bar per character, green as each is typed, and a
  // count. Spaces and dashes do not count (v1 reads them as separators);
  // past 17 it turns red. The red hairline of an empty box goes once it is
  // filled.
  var vin = document.getElementById("jc1-vin");
  var meter = document.querySelector(".jc1-vin-meter");
  if (vin && meter) {
    var bars = Array.from(meter.querySelectorAll(".jc1-vin-dots i"));
    var counter = meter.querySelector(".jc1-vin-count");
    var showVin = function () {
      var count = vin.value.replace(/[\s-]+/g, "").length;
      bars.forEach(function (bar, i) {
        bar.classList.toggle("is-on", i < count);
      });
      counter.textContent = count + "/" + bars.length;
      meter.classList.toggle("is-done", count === bars.length);
      meter.classList.toggle("is-over", count > bars.length);
      vin.classList.toggle("is-empty", vin.value.trim() === "");
    };
    vin.addEventListener("input", showVin);
    showVin();
  }

  document.querySelectorAll("[data-autorows]").forEach(function (list) {
    var template = document.getElementById(list.dataset.autorows);
    list.addEventListener("input", function (event) {
      var row = event.target.closest("tr, .jc1-row");
      var rows = rowsOf(list);
      if (row === rows[rows.length - 1] && hasContent(row)) {
        row.classList.remove("is-open");
        list.appendChild(template.content.firstElementChild.cloneNode(true));
      }
      renumber(list);
    });
  });
})();
