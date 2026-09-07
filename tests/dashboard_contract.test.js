"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { completionCopy, selectedIdInTickets } = require("../parcelco/static/js/dashboard_contract.js");

test("completion copy distinguishes every Reflect outcome", () => {
  const reasons = ["learned", "holdout", "clean_pass", "blocked", "rejected"];
  const titles = reasons.map((reason) =>
    completionCopy({ reflect_reason: reason, langfuse_on: false, trace_available: false }).title
  );
  assert.equal(new Set(titles).size, reasons.length);
  assert.match(titles[0], /kept a lesson/);
  assert.match(titles[1], /holdout scored/);
  assert.match(titles[2], /clean PASS/);
  assert.match(titles[3], /lesson blocked/);
  assert.match(titles[4], /no safe lesson/);
});

test("LangFuse-off completion says no trace was written", () => {
  const copy = completionCopy({ reflect_reason: "learned", langfuse_on: false });
  assert.match(copy.body, /appended to learnings\.md/);
  assert.match(copy.body, /no trace was written/);
  assert.doesNotMatch(copy.body, /trace is available/);
});

test("trace copy is only positive when this run exposes a trace", () => {
  const missing = completionCopy({ reflect_reason: "clean_pass", langfuse_on: true });
  const available = completionCopy({
    reflect_reason: "clean_pass",
    langfuse_on: true,
    trace_available: true,
  });
  assert.match(missing.body, /no verified trace is available/);
  assert.match(available.body, /trace is available for this run/);
});

test("filtered ticket lists never preserve a hidden selection", () => {
  const holdout = [{ id: "B01" }, { id: "B02" }];
  assert.equal(selectedIdInTickets(holdout, "A01"), "B01");
  assert.equal(selectedIdInTickets(holdout, "B02"), "B02");
  assert.equal(selectedIdInTickets([], "B02"), null);
});
