(function (root, factory) {
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  root.ParcelCoDashboardContract = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function completionCopy(event) {
    const ev = event || {};
    const inspector = ev.inspector || {};
    const autonomous = inspector.autonomous || {};
    const evidence = ev.langfuse_evidence || inspector.langfuse_evidence || {};
    const reason = ev.reflect_reason || autonomous.reason || "unchanged";
    const langfuseOn = ev.langfuse_on === true || evidence.enabled === true;
    const traceAvailable = ev.trace_available === true;

    const byReason = {
      learned: [
        "Done — Reflect kept a lesson",
        "The lesson was appended to learnings.md.",
      ],
      holdout: [
        "Done — holdout scored; memory unchanged",
        "Holdout tickets skip Reflect so they can measure generalization.",
      ],
      clean_pass: [
        "Done — clean PASS; nothing to learn",
        "The first draft passed, so Reflect correctly left learnings.md unchanged.",
      ],
      blocked: [
        "Done — lesson blocked; memory unchanged",
        "Reflect drafted a lesson, but the safety filter rejected the write.",
      ],
      rejected: [
        "Done — no safe lesson; memory unchanged",
        "Reflect found no safe reusable lesson to write.",
      ],
      unchanged: [
        "Done — run complete; memory unchanged",
        "This run did not add a lesson.",
      ],
    };
    const selected = byReason[reason] || byReason.unchanged;
    let traceCopy;
    if (traceAvailable) {
      traceCopy = "A LangFuse trace is available for this run.";
    } else if (!langfuseOn) {
      traceCopy = "LangFuse was off, so verification was checklist-only and no trace was written.";
    } else {
      traceCopy = "LangFuse was on, but no verified trace is available for this run.";
    }
    return { title: selected[0], body: `${selected[1]} ${traceCopy}`, reason };
  }

  function selectedIdInTickets(tickets, selectedId) {
    const rows = Array.isArray(tickets) ? tickets : [];
    if (selectedId && rows.some((ticket) => ticket && ticket.id === selectedId)) return selectedId;
    return rows.length && rows[0] ? rows[0].id : null;
  }

  return { completionCopy, selectedIdInTickets };
});
