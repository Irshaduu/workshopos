// Tests for apps/billing/static/billing/bill.js, with Node's own test runner (ADR-0020):
//
//     node --test "tests/js/*.test.js"
//
// They test the plain functions. The sheet's fit and the chip on a real page are checked in
// a browser.

import assert from "node:assert/strict";
import { test } from "node:test";

import { chipWords, scaleFor } from "../../apps/billing/static/billing/bill.js";

// The words the page sends, as Django gives them (billing/bill.html).
const WORDS = {
  today: "Today",
  empty: "Pick the day",
  months: "Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec".split("|"),
};

test("a bill wider than the screen is scaled down to fit it", () => {
  assert.equal(scaleFor(397, 794), 0.5);
});

test("a bill is never scaled up, and a screen as wide as it leaves it as it prints", () => {
  assert.equal(scaleFor(1200, 794), 1);
  assert.equal(scaleFor(794, 794), 1);
});

test("a bill not drawn yet, or no room at all, is left as it is", () => {
  assert.equal(scaleFor(400, 0), 1);
  assert.equal(scaleFor(0, 794), 1);
});

test("today reads as Today, in the word the page sends", () => {
  assert.deepEqual(chipWords("2026-11-10", "2026-11-10", WORDS), {
    words: "Today",
    backDated: false,
  });
});

test("another day reads as every date on the page does, and shows in amber", () => {
  assert.deepEqual(chipWords("2026-11-08", "2026-11-10", WORDS), {
    words: "8 Nov 2026",
    backDated: true,
  });
  // Sep, as Django writes it, never the browser's own Sept.
  assert.equal(chipWords("2026-09-08", "2026-11-10", WORDS).words, "8 Sep 2026");
});

test("an empty or broken box asks for a day, and is not amber", () => {
  for (const value of ["", "not a day", "2026-13-01"]) {
    assert.deepEqual(chipWords(value, "2026-11-10", WORDS), {
      words: "Pick the day",
      backDated: false,
    });
  }
});
