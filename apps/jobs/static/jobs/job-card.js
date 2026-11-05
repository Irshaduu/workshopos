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

  choices.addEventListener("change", (event) => {
    if (event.target.name === "colour") {
      const word = event.target.value;
      const own = word === "other" ? other.value : "";
      for (const element of painted()) {
        paint(element, word, own);
      }
      const name = event.target.closest("label").textContent.trim();
      swatch.setAttribute("aria-label", `${swatch.dataset.word} ${name}`);
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
