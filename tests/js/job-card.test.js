// Tests for apps/jobs/static/jobs/job-card.js, with Node's own test runner (ADR-0020):
//
//     node --test "tests/js/*.test.js"
//
// They test the plain functions. Typing into the open row, the colour choices and the
// meter are checked in a browser.

import assert from "node:assert/strict";
import { test } from "node:test";

import { numbered, vinCount } from "../../apps/jobs/static/jobs/job-card.js";

test("JOB-19: spaces and dashes do not count in a VIN", () => {
  assert.equal(vinCount(""), 0);
  assert.equal(vinCount("WBA8E9C50GK123456"), 17);
  assert.equal(vinCount("WBA 8E9C-50GK 123456"), 17);
  assert.equal(vinCount("  WBA  "), 3);
});

test("JOB-35: a new row takes the next number in every name", () => {
  const blank = '<input name="concerns-__prefix__-text" id="id_concerns-__prefix__-text">';

  assert.equal(numbered(blank, "3"), '<input name="concerns-3-text" id="id_concerns-3-text">');
});
