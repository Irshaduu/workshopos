// Tests for apps/jobs/static/jobs/job-card.js, with Node's own test runner (ADR-0020):
//
//     node --test "tests/js/*.test.js"
//
// They test the plain functions. Typing into the open row, the colour choices, the meter
// and the known plate's fill are checked in a browser.

import assert from "node:assert/strict";
import { test } from "node:test";

import {
  GROUPS,
  groupFill,
  mayWrite,
  numbered,
  stillFilled,
  stillPainted,
  vinCount,
} from "../../apps/jobs/static/jobs/job-card.js";

test("KNOWN-5: an empty box, or one still holding what the fill wrote, may be written", () => {
  assert.equal(mayWrite("", undefined, false), true);
  assert.equal(mayWrite("   ", undefined, false), true);
  assert.equal(mayWrite("BMW", "BMW", false), true);
});

test("KNOWN-5: a box a person typed in, or emptied, is never written", () => {
  assert.equal(mayWrite("Audi", "BMW", false), false);
  assert.equal(mayWrite("Audi", undefined, false), false);
  assert.equal(mayWrite("", "BMW", true), false);
  assert.equal(mayWrite("BMW", "BMW", true), false);
});

test("KNOWN-4: a group is written whole, or not at all", () => {
  const brand = { name: "brand", value: "", written: undefined, typed: false };
  const model = { name: "car_model", value: "", written: undefined, typed: false };
  const answer = { brand: "BMW", car_model: "520d" };

  assert.deepEqual(groupFill([brand, model], answer), ["BMW", "520d"]);
  assert.equal(groupFill([brand, { ...model, value: "X5", typed: true }], answer), null);
});

test("KNOWN-5: a plate that names no car takes back what the fill wrote", () => {
  const brand = { name: "brand", value: "BMW", written: "BMW", typed: false };
  const model = { name: "car_model", value: "520d", written: "520d", typed: false };

  assert.deepEqual(groupFill([brand, model], null), ["", ""]);
});

test("KNOWN-4: a box the answer has nothing for is emptied, never left with another car's", () => {
  const vin = { name: "vin", value: "WBA8E9C50GK123456", written: "WBA8E9C50GK123456" };

  assert.deepEqual(groupFill([vin], { brand: "BMW" }), [""]);
});

test("KNOWN-4: the brand and the model are one group, and the codes are their own", () => {
  assert.deepEqual(GROUPS, [["brand", "car_model"], ["chassis_code"], ["vin"]]);
});

test("KNOWN-5: a page that came back knows a box still holds what the car holds", () => {
  assert.equal(stillFilled("G30", "G30"), true);
  assert.equal(stillFilled("F10", "G30"), false);
  assert.equal(stillFilled("", ""), false);
});

test("KNOWN-5: on a page that came back, Other's own colour is part of what the car holds", () => {
  const other = { colour: "other", colour_other: "#111111" };
  assert.equal(stillPainted("other", "#111111", other), true);
  assert.equal(stillPainted("other", "#222222", other), false);
  assert.equal(stillPainted("red", "#808080", { colour: "red", colour_other: "" }), true);
  assert.equal(stillPainted("red", "#808080", other), false);
});

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
