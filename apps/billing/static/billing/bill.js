// A job card's bill (docs/rules/settle-bill.md). It only shows: the server works out every
// figure, the check included, and a script never works out money (CONTRIBUTING.md).

// How much to scale the bill so it fits: never bigger than it prints, and smaller only on a
// screen narrower than A4 (v1's fitSheet).
export function scaleFor(available, natural) {
  if (!natural || available <= 0 || available >= natural) {
    return 1;
  }
  return available / natural;
}

// The date chip's words for a day typed as YYYY-MM-DD: Today, or the day as every date on the
// page reads, like 9 Sep 2026 (docs/DESIGN.md), which then shows in amber. The page gives the
// words, the month words included, as Django shows them. An empty box asks for a day. Only the
// server decides which days may be chosen.
export function chipWords(value, today, words) {
  if (value && value === today) {
    return { words: words.today, backDated: false };
  }
  const parts = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value || "");
  const month = parts ? words.months[Number(parts[2]) - 1] : undefined;
  if (!month) {
    return { words: words.empty, backDated: false };
  }
  return { words: `${Number(parts[3])} ${month} ${parts[1]}`, backDated: true };
}

if (typeof document !== "undefined") {
  const wrap = document.querySelector(".sheet-wrap");
  const sheet = document.querySelector(".sheet");
  let width = 0;

  // Fits the bill again only when the room for it changed, unless asked to, as after its
  // fonts load or a print, when the bill itself may have changed size.
  const fit = (again = false) => {
    if (!again && wrap.clientWidth === width) {
      return;
    }
    sheet.style.transform = "";
    wrap.style.height = "";
    width = wrap.clientWidth;
    const scale = scaleFor(width, sheet.offsetWidth);
    if (scale < 1) {
      sheet.style.transform = `scale(${scale})`;
      wrap.style.height = `${sheet.offsetHeight * scale}px`;
    }
  };

  if (wrap && sheet) {
    fit(true);
    window.addEventListener("resize", () => fit());
    document.fonts?.ready.then(() => fit(true));
    window.addEventListener("beforeprint", () => {
      sheet.style.transform = "";
      wrap.style.height = "";
    });
    window.addEventListener("afterprint", () => fit(true));
  }

  // The chip under Date paid shows the day the box holds (the box itself is see-through, on
  // top of the chip, so a tap opens the device's own date picker).
  const chip = document.querySelector("[data-date-chip]");
  if (chip) {
    const box = chip.querySelector("input");
    const shown = chip.querySelector("[data-date-words]");
    const words = {
      today: shown.dataset.today,
      empty: shown.dataset.empty,
      months: shown.dataset.months.split("|"),
    };
    const show = () => {
      const chosen = chipWords(box.value, box.max, words);
      shown.textContent = chosen.words;
      chip.classList.toggle("pay__date--back-dated", chosen.backDated);
    };
    show();
    box.addEventListener("change", show);
    // A tap on a phone opens the device's picker by itself. A laptop's Chrome and Edge open it
    // only from the box's own calendar icon, which the chip hides, so a click asks for it. On
    // a phone it is open already, and asking again throws (v1).
    chip.addEventListener("click", () => {
      try {
        box.showPicker?.();
      } catch {
        // Open already.
      }
    });
  }
}
