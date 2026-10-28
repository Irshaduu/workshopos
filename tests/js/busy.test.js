// Tests for static/js/busy.js, with Node's own test runner (ADR-0020):
//
//     node --test "tests/js/*.test.js"
//
// They test the plain functions on stand-in forms and buttons. The real
// taps are checked in a browser.

import assert from "node:assert/strict";
import { test } from "node:test";

import { claim, release } from "../../static/js/busy.js";

function fakeButton() {
  const attributes = new Map();
  return {
    getAttribute: (name) => attributes.get(name) ?? null,
    setAttribute: (name, value) => attributes.set(name, String(value)),
    removeAttribute: (name) => attributes.delete(name),
  };
}

const isBusy = (button) => button.getAttribute("aria-busy") === "true";

function fakeForm(...buttons) {
  return {
    dataset: {},
    querySelectorAll(selector) {
      assert.equal(selector, '[aria-busy="true"]');
      return buttons.filter(isBusy);
    },
  };
}

function fakePage(...forms) {
  return {
    querySelectorAll(selector) {
      assert.equal(selector, "form[data-sending]");
      return forms.filter((form) => "sending" in form.dataset);
    },
  };
}

test("SIGN-14: the first tap sends the form and shows its button busy", () => {
  const button = fakeButton();
  const form = fakeForm(button);

  assert.equal(claim(form, button), true);
  assert.equal(isBusy(button), true);
});

test("SIGN-14: a second tap or Enter sends nothing while the form is sending", () => {
  const button = fakeButton();
  const form = fakeForm(button);
  claim(form, button);

  assert.equal(claim(form, button), false);
  assert.equal(claim(form, undefined), false);
});

test("SIGN-14: a tap on another button of the same form sends nothing", () => {
  const first = fakeButton();
  const second = fakeButton();
  const form = fakeForm(first, second);
  claim(form, first);

  assert.equal(claim(form, second), false);
  assert.equal(isBusy(second), false);
});

test("each form has its own guard", () => {
  const sent = fakeForm(fakeButton());
  claim(sent, undefined);
  const button = fakeButton();

  assert.equal(claim(fakeForm(button), button), true);
});

test("SIGN-14: a form sent with Enter and no button still sends only once", () => {
  const form = fakeForm();

  assert.equal(claim(form, undefined), true);
  assert.equal(claim(form, undefined), false);
});

test("after Back, the page's forms send again and no button looks busy", () => {
  const button = fakeButton();
  const form = fakeForm(button);
  claim(form, button);

  release(fakePage(form));

  assert.equal(isBusy(button), false);
  assert.equal(claim(form, button), true);
});
