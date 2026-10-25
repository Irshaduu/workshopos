// Tests for static/js/sound.js, with Node's own test runner (ADR-0020):
//
//     node --test "tests/js/*.test.js"
//
// They test the plain functions. Playing a sound needs a browser.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  chooseTone,
  isEnabled,
  loudness,
  PEAK_LIMIT,
  TONES,
} from "../../static/js/sound.js";

const OUTCOMES = ["success", "error", "warning"];

test("a success notice plays the success tone", () => {
  assert.equal(chooseTone(["success"]), "success");
});

test("info, debug and unknown notices stay silent", () => {
  assert.equal(chooseTone([]), null);
  assert.equal(chooseTone(["info"]), null);
  assert.equal(chooseTone(["debug"]), null);
  assert.equal(chooseTone(["something else"]), null);
});

test("one sound per page: an error wins wherever it is", () => {
  assert.equal(chooseTone(["success", "error"]), "error");
  assert.equal(chooseTone(["error", "success"]), "error");
  assert.equal(chooseTone(["warning", "info", "error"]), "error");
});

test("with no error, the first notice that sounds decides", () => {
  assert.equal(chooseTone(["info", "warning", "success"]), "warning");
  assert.equal(chooseTone(["success", "warning"]), "success");
});

test("sound is on unless this device turned it off", () => {
  assert.equal(isEnabled(null), true);
  assert.equal(isEnabled("on"), true);
  assert.equal(isEnabled("off"), false);
});

test("no note is loud enough to distort the speaker", () => {
  for (const notes of Object.values(TONES)) {
    for (const [, , , peak] of notes) {
      assert.ok(loudness(peak) > 0);
      assert.ok(loudness(peak) <= PEAK_LIMIT);
    }
  }
});

test("the question tone is quieter than every outcome tone", () => {
  const loudest = (tone) => Math.max(...TONES[tone].map((n) => loudness(n[3])));
  for (const outcome of OUTCOMES) {
    assert.ok(loudest("prompt") < loudest(outcome), outcome);
  }
});

test("success rises and error falls, so they are told apart by ear", () => {
  const [first, second] = TONES.success;
  assert.ok(second[0] > first[0]);
  const [high, low] = TONES.error;
  assert.ok(low[0] < high[0]);
});
