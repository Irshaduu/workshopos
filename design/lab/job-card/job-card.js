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
  var bars = Array.from(meter.querySelectorAll(".jc1-vin-dots i"));
  var counter = meter.querySelector(".jc1-vin-count");
  function showVin() {
    var count = vin.value.replace(/[\s-]+/g, "").length;
    bars.forEach(function (bar, i) {
      bar.classList.toggle("is-on", i < count);
    });
    counter.textContent = count + "/" + bars.length;
    meter.classList.toggle("is-done", count === bars.length);
    meter.classList.toggle("is-over", count > bars.length);
    vin.classList.toggle("is-empty", vin.value.trim() === "");
  }
  vin.addEventListener("input", showVin);
  showVin();

  // Unsaved work: the head turns amber and the changed box gets its edge (v1's jc-dirty).
  var head = document.getElementById("jc1-head");
  var form = document.getElementById("jc1-form");
  form.addEventListener("input", function (event) {
    head.classList.add("is-dirty");
    if (event.target.matches(".jc1-input")) {
      event.target.classList.add("is-changed");
    }
  });

  // Known plate and Question show a new card that a known plate filled
  // (docs/rules/known-plate.md). In the app the server sends what it knows, and the
  // page's script writes it only into boxes nobody typed in. Here it is written at once.
  var filledValues = {
    "jc1-reg": "KL00AB0002",
    "jc1-brand": "BMW",
    "jc1-model": "520d",
    "jc1-chassis": "G30",
    "jc1-vin": "WBA00000000000001",
    "jc1-km": "",
    "jc1-cust": "",
    "jc1-contact": "",
    "jc1-note": ""
  };
  var savedValues = {};
  Object.keys(filledValues).forEach(function (id) {
    savedValues[id] = document.getElementById(id).value;
  });
  // The last customer, offered as the two boxes' greyed words, never as their values.
  var offer = { "jc1-cust": "Arun K.", "jc1-contact": "00000 00000" };

  // The State switch: a cancelled card locks every box at once. In the app the server
  // writes the lock. The note also takes its one-row start here.
  function showState() {
    var isNew = document.getElementById("state-new").checked;
    var isKnown = document.getElementById("state-known").checked;
    var filled = isKnown || document.getElementById("state-question").checked;
    form.disabled = document.getElementById("state-cancelled").checked;
    head.classList.toggle("paint-unset", isNew);
    head.classList.toggle("paint-black", !isNew);
    head.classList.toggle("is-dirty", filled);
    Object.keys(filledValues).forEach(function (id) {
      var box = document.getElementById(id);
      box.value = filled ? filledValues[id] : savedValues[id];
      box.classList.toggle("is-changed", filled && filledValues[id] !== "");
    });
    Object.keys(offer).forEach(function (id) {
      var box = document.getElementById(id);
      if (isKnown) {
        box.setAttribute("placeholder", offer[id]);
      } else {
        box.removeAttribute("placeholder");
      }
      box.classList.toggle("is-offered", isKnown);
    });
    useLast.hidden = false;
    var chassis = document.getElementById("jc1-chassis");
    chassis.classList.toggle("is-empty", chassis.value === "");
    showVin();
  }

  // The offer shows only while both boxes are empty. Use last visit copies both.
  var useLast = document.getElementById("jc1-use-last");
  function endOffer() {
    Object.keys(offer).forEach(function (id) {
      var box = document.getElementById(id);
      box.removeAttribute("placeholder");
      box.classList.remove("is-offered");
    });
    useLast.hidden = true;
  }
  useLast.addEventListener("click", function () {
    Object.keys(offer).forEach(function (id) {
      var box = document.getElementById(id);
      box.value = offer[id];
      box.classList.add("is-changed");
    });
    endOffer();
  });
  Object.keys(offer).forEach(function (id) {
    document.getElementById(id).addEventListener("input", function () {
      if (Object.keys(offer).some(function (key) { return document.getElementById(key).value !== ""; })) {
        endOffer();
      }
    });
  });
  document.querySelectorAll('input[name="state"]').forEach(function (box) {
    box.addEventListener("change", showState);
  });
  showState();

  // The colour choices: a pick paints the swatch, the head's rail and its dot, and closes
  // the choices, except Other, which waits for its own colour box.
  var swatch = document.getElementById("jc1-swatch");
  var dot = document.querySelector(".jc1-dot");
  var choices = document.getElementById("jc1-colours");
  var other = document.getElementById("jc1-other");
  function paint(name, custom) {
    [swatch, head, dot].forEach(function (el) {
      Array.from(el.classList).forEach(function (word) {
        if (word.startsWith("paint-")) { el.classList.remove(word); }
      });
      el.classList.add(name);
      if (custom) {
        el.style.setProperty("--paint", custom);
      } else {
        el.style.removeProperty("--paint");
      }
    });
  }
  choices.addEventListener("change", function (event) {
    if (event.target.name === "colour") {
      swatch.setAttribute("aria-label", "Car colour: " + event.target.closest("label").textContent.trim());
      head.classList.add("is-dirty");
      if (event.target.value === "paint-other") {
        paint("paint-other", other.value);
      } else {
        paint(event.target.value);
        choices.hidePopover();
      }
    }
  });
  other.addEventListener("input", function () {
    paint("paint-other", other.value);
  });

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
