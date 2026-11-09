// The job card's page (docs/rules/job-card.md). It only shows: the server decides
// everything, and the page saves with no script, with one open row after each save.

const VIN_LENGTH = 17;

// How many characters a VIN box holds. Spaces and dashes are how a VIN is written in groups,
// so they do not count (JOB-19).
export function vinCount(typed) {
  return typed.replace(/[\s-]+/g, "").length;
}

// The name of a new row's boxes, from the blank row's: Django numbers them from the
// list's count of rows (JOB-35).
export function numbered(html, index) {
  return html.replaceAll("__prefix__", String(index));
}

// The groups a known plate fills, each whole or not at all, so a card never shows one car's
// brand beside another car's model (KNOWN-4). The answer's data has the form's names for its
// boxes. The colour is a group of its own, below.
export const GROUPS = [["brand", "car_model"], ["chassis_code"], ["vin"]];

// Whether the fill may write a box: nobody typed in it, and it holds what the fill last
// wrote, or nothing. Emptying a box counts as typing (KNOWN-5).
export function mayWrite(value, written, typed) {
  return !typed && (value.trim() === "" || value === written);
}

// What the fill writes into a group's boxes: each box's new value from the answer, or
// nothing when the plate named no car; or null when one of its boxes may not be written.
export function groupFill(boxes, answer) {
  if (!boxes.every((box) => mayWrite(box.value, box.written, box.typed))) {
    return null;
  }
  return boxes.map((box) => (answer ? (answer[box.name] ?? "") : ""));
}

// Whether a box on a page that came back still holds what the fill wrote there: what the car
// holds. That page has no memory of its own (KNOWN-5).
export function stillFilled(value, held) {
  return value !== "" && value === held;
}

// The same for the colour, where Other's own colour is part of what the car holds.
export function stillPainted(word, own, held) {
  return word === (held.colour ?? "") && (word !== "other" || own === held.colour_other);
}

// Everything below needs a browser.

function showVinMeter(box, meter) {
  const bars = Array.from(meter.querySelectorAll(".job-vin-bars i"));
  const count = vinCount(box.value);
  bars.forEach((bar, i) => {
    bar.classList.toggle("is-on", i < count);
  });
  meter.querySelector(".job-vin-count").textContent = `${count}/${VIN_LENGTH}`;
  meter.classList.toggle("is-done", count === VIN_LENGTH);
  meter.classList.toggle("is-over", count > VIN_LENGTH);
}

// A pick paints the head's rail, its dot and the swatch. A page has no inline style, so Other's
// own colour is set from here (JOB-21).
function paint(element, word, ownColour) {
  for (const name of Array.from(element.classList)) {
    if (name.startsWith("paint-")) {
      element.classList.remove(name);
    }
  }
  element.classList.add(`paint-${word || "unset"}`);
  if (ownColour) {
    element.style.setProperty("--paint", ownColour);
  } else {
    element.style.removeProperty("--paint");
  }
}

function openTheNextRow(list, row) {
  const section = list.parentElement;
  const count = section.querySelector('input[name$="-TOTAL_FORMS"]');
  const blank = section.querySelector("template[data-row-template]");
  const holder = document.createElement("template");
  holder.innerHTML = numbered(blank.innerHTML, count.value);
  row.classList.remove("is-open");
  list.append(holder.content);
  count.value = String(Number(count.value) + 1);
}

function startPage(form) {
  const head = document.getElementById("job-head");
  // A refused page comes back with what was typed, so it is unsaved from the start.
  let dirty = head.classList.contains("is-dirty");

  function markDirty(box) {
    dirty = true;
    head.classList.add("is-dirty");
    if (box?.classList.contains("job-input")) {
      box.classList.add("is-changed");
    }
  }

  form.addEventListener("input", (event) => markDirty(event.target));
  form.addEventListener("change", (event) => markDirty(event.target));

  // Leaving with something typed and not saved asks first (JOB-47).
  window.addEventListener("beforeunload", (event) => {
    if (dirty) {
      event.preventDefault();
      event.returnValue = "";
    }
  });
  form.addEventListener("submit", () => {
    dirty = false;
  });

  // Each list keeps one open row at its end, and typing into it opens the next (JOB-35).
  for (const list of form.querySelectorAll("[data-rows]")) {
    list.addEventListener("input", (event) => {
      const row = event.target.closest(".job-row");
      if (row?.classList.contains("is-open") && event.target.matches(".job-input")) {
        if (event.target.value.trim() !== "") {
          openTheNextRow(list, row);
        }
      }
    });
  }

  const vin = form.querySelector('input[name="vin"]');
  const meter = form.querySelector("[data-vin-meter]");
  vin.addEventListener("input", () => showVinMeter(vin, meter));
  showVinMeter(vin, meter);

  // A pick paints, and closes the choices, except Other, which waits for its colour box.
  const swatch = document.getElementById("job-swatch");
  const choices = document.getElementById("job-colours");
  const other = form.querySelector('input[name="colour_other"]');
  const painted = () => [swatch, head, document.querySelector(".job-dot")].filter(Boolean);

  // Paints the rail, the dot and the swatch, and tells a screen reader the colour's name.
  function repaint(word, own) {
    for (const element of painted()) {
      paint(element, word, own);
    }
    const radio = form.querySelector(`input[name="colour"][value="${word}"]`);
    const name = radio?.closest("label").textContent.trim() ?? "";
    swatch.setAttribute("aria-label", `${swatch.dataset.word} ${name}`);
  }

  choices.addEventListener("change", (event) => {
    if (event.target.name === "colour") {
      const word = event.target.value;
      repaint(word, word === "other" ? other.value : "");
      if (word !== "other") {
        choices.hidePopover();
      }
    }
  });
  other.addEventListener("input", () => {
    for (const element of painted()) {
      paint(element, "other", other.value);
    }
  });

  const holder = document.getElementById("known-plate");
  if (holder) {
    startKnownPlate(form, holder, {
      markDirty,
      repaint,
      showMeter: () => showVinMeter(vin, meter),
    });
  }
}

// A known plate fills a new card (docs/rules/known-plate.md). The server answers into the
// holder under the plate box, with what it knows as data; the rules are the server's, and
// this only writes it into boxes nobody typed in (KNOWN-4 to KNOWN-7).
function startKnownPlate(form, holder, page) {
  const box = (name) => form.elements.namedItem(name);
  const written = new Map();
  const typed = new Set();
  // A person's typing or pick fires this; a script's writing does not.
  form.addEventListener("input", (event) => typed.add(event.target.name));

  function fill(answer) {
    let wrote = false;
    for (const group of GROUPS) {
      const boxes = group.map((name) => ({
        name,
        value: box(name).value,
        written: written.get(name),
        typed: typed.has(name),
      }));
      const values = groupFill(boxes, answer);
      if (values === null) {
        continue;
      }
      group.forEach((name, i) => {
        const element = box(name);
        if (element.value !== values[i]) {
          element.value = values[i];
          wrote = true;
        }
        element.classList.toggle("is-changed", element.value !== element.defaultValue);
        written.set(name, values[i]);
      });
    }
    // The colour, with Other's own colour, whole. box("colour") is the list of its choices.
    const colour = box("colour");
    const ownColour = box("colour_other");
    const colourTyped = typed.has("colour") || typed.has("colour_other");
    if (mayWrite(colour.value, written.get("colour"), colourTyped)) {
      const word = answer?.colour ?? "";
      const own = word === "other" ? answer.colour_other : "";
      if (colour.value !== word) {
        // Each choice by itself: a list of choices ignores an empty value, so the first car's
        // colour would stay picked.
        for (const choice of colour) {
          choice.checked = choice.value === word;
        }
        wrote = true;
      }
      ownColour.value = own || ownColour.defaultValue;
      written.set("colour", word);
      page.repaint(word, own);
    }
    if (wrote) {
      page.markDirty();
    }
    page.showMeter();
  }

  // The last customer, offered, never filled: their name and number as the two boxes' greyed
  // words, with Use last visit, only while both are empty (KNOWN-7). Floor's page has neither
  // box nor button, and its answer has no customer (KNOWN-8).
  const useLast = document.getElementById("job-use-last");
  let offer = null;
  let opened = false;

  function showOffer() {
    if (!useLast) {
      return;
    }
    const boxes = [
      [box("customer_name"), offer?.name],
      [box("contact_number"), offer?.number],
    ];
    const on = offer !== null && boxes.every(([element]) => element.value.trim() === "");
    for (const [element, value] of boxes) {
      if (on && value) {
        element.setAttribute("placeholder", value);
      } else {
        element.removeAttribute("placeholder");
      }
      element.classList.toggle("is-offered", Boolean(on && value));
    }
    // Opened once, when the offer first shows, and never again over a section someone closed.
    if (on && !opened) {
      useLast.closest("details").open = true;
      opened = true;
    }
    useLast.hidden = !on;
  }

  function offerFrom(answer) {
    offer =
      answer && "customer_name" in answer
        ? { name: answer.customer_name, number: answer.contact_number }
        : null;
    showOffer();
  }

  if (useLast) {
    useLast.addEventListener("click", () => {
      box("customer_name").value = offer.name;
      box("contact_number").value = offer.number;
      page.markDirty(box("customer_name"));
      page.markDirty(box("contact_number"));
      showOffer();
    });
    box("customer_name").addEventListener("input", showOffer);
    box("contact_number").addEventListener("input", showOffer);
  }

  const answerOnThePage = () => holder.querySelector("[data-known]")?.dataset ?? null;

  // A page that comes back after a refused save or a question has the plate's answer with it,
  // so what the fill wrote can still be swapped or taken back, and the offer stays (KNOWN-5).
  const cameBack = answerOnThePage();
  if (cameBack) {
    for (const name of GROUPS.flat()) {
      if (stillFilled(box(name).value, cameBack[name] ?? "")) {
        written.set(name, box(name).value);
      }
    }
    if (stillPainted(box("colour").value, box("colour_other").value, cameBack)) {
      written.set("colour", box("colour").value);
    }
    offerFrom(cameBack);
  }

  // htmx 4 sends htmx:before:request to the box that asked, and htmx:after:settle to the part
  // of the page that changed: this holder (measured in the browser, htmx 4.0.1). An answer is
  // dropped when the plate changed while it was on its way (KNOWN-5).
  const plate = box("plate");
  let asked = null;
  plate.addEventListener("htmx:before:request", () => {
    asked = plate.value;
  });
  holder.addEventListener("htmx:after:settle", () => {
    if (plate.value === asked) {
      const answer = answerOnThePage();
      fill(answer);
      offerFrom(answer);
    }
  });
}

if (typeof document !== "undefined") {
  // Other's own colour, on a saved card.
  for (const element of document.querySelectorAll("[data-paint]")) {
    element.style.setProperty("--paint", element.dataset.paint);
  }
  const form = document.getElementById("job-form");
  if (form) {
    startPage(form);
  }
}
