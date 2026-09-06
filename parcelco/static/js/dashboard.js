(() => {
  const fmt = (x) => (x == null || Number.isNaN(x) ? "—" : `${(100 * x).toFixed(0)}%`);
  const fmtDelta = (x) => {
    if (x == null || Number.isNaN(x)) return "—";
    const pp = (100 * x).toFixed(0);
    return `${x > 0 ? "+" : ""}${pp}pp`;
  };
  const el = (id) => document.getElementById(id);

  const state = {
    tickets: [],
    selectedId: null,
    selected: null,
    split: "",
    query: "",
    history: [],
    events: [],
    busy: false,
    seenNodes: new Set(),
  };

  const chart = new Chart(el("chart"), {
    type: "line",
    data: {
      labels: [],
      datasets: [
        { label: "Learn set", data: [], borderColor: "#ff6d5a", tension: 0.25, fill: false },
        { label: "Holdout", data: [], borderColor: "#3ecf8e", tension: 0.25, fill: false },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: "#8b96a8" } } },
      scales: {
        x: { ticks: { color: "#8b96a8" }, grid: { color: "#2a3340" } },
        y: {
          min: 0,
          max: 1,
          ticks: { color: "#8b96a8", callback: (v) => `${Math.round(100 * v)}%` },
          grid: { color: "#2a3340" },
        },
      },
    },
  });

  function setGuide(title, body) {
    el("guide-title").textContent = title;
    el("guide-body").textContent = body;
  }

  function setTeach(step) {
    const copy = {
      pick: [
        "① Click a ticket on the left",
        "Then press the orange button. The LLM only writes the reply — the checklist grades it.",
      ],
      run: [
        "② Autonomous loop running…",
        "Retrieve → Generate → Evaluate → Heal → Reflect (learn-set). Holdout skips Reflect.",
      ],
      heal: [
        "③ Healing — LLM rewrites",
        "Checklist failed. Harness asks the LLM to try again. Then Reflect may write a lesson.",
      ],
      learn: [
        "④ Suite proof — Score / batch Learn",
        "Big suite (700+300) measures lift. Per-ticket Reflect already learns on learn-set runs.",
      ],
      done: [
        "Done — Reflect may have updated learnings.md",
        "Check “What Reflect learned” and expand Memory. Score suite to see lift on the big set.",
      ],
    };
    const [title, body] = copy[step] || copy.pick;
    setGuide(title, body);
  }

  function setBusy(busy, label) {
    state.busy = busy;
    const pill = el("busy");
    pill.textContent = label || (busy ? "busy" : "idle");
    pill.classList.toggle("busy", !!busy);
    ["btn-run", "btn-baseline", "btn-improve", "btn-reset"].forEach((id) => {
      const b = el(id);
      if (b) b.disabled = !!busy || (id === "btn-run" && !state.selectedId);
    });
  }

  function highlightNode(node) {
    if (!node) return;
    state.seenNodes.add(node);
    document.querySelectorAll(".node").forEach((d) => {
      const key = d.dataset.node;
      d.classList.toggle("active", key === node);
      d.classList.toggle("done", state.seenNodes.has(key) && key !== node);
    });
    if (node === "retrieve" || node === "generate") setTeach("run");
    if (node === "evaluate" || node === "heal") setTeach("heal");
    if (node === "reflect" || node === "suite" || node === "improve") setTeach("learn");
  }

  function setNodeBody(node, text) {
    const n = el(`node-${node}`);
    if (n && text) n.textContent = String(text).slice(0, 160);
  }

  async function loadTickets() {
    const params = new URLSearchParams();
    if (state.split) params.set("split", state.split);
    if (state.query) params.set("q", state.query);
    const data = await (await fetch(`/api/tickets?${params}`)).json();
    state.tickets = data.tickets || [];
    syncSuiteChips(data.suite);
    if (!data.suite) {
      el("ticket-count").textContent = String(data.count || 0);
    }
    renderTicketList();
    if (!state.selectedId && state.tickets.length) selectTicket(state.tickets[0].id);
  }

  function syncSuiteChips(suite) {
    if (!suite) return;
    const mode = suite.mode || "full";
    document.querySelectorAll("[data-suite]").forEach((b) => {
      b.classList.toggle("active", b.dataset.suite === mode);
    });
    const count = el("ticket-count");
    if (count && suite.active_total != null) {
      count.textContent =
        mode === "demo"
          ? `${suite.active_total} demo / ${suite.catalog_total} cat`
          : String(suite.active_total);
    }
    if (el("suite-mode")) el("suite-mode").textContent = mode;
    if (el("suite-size") && suite.active_improve != null) {
      el("suite-size").textContent = `${suite.active_improve}A / ${suite.active_holdout}B`;
    }
  }

  async function setSuiteMode(mode) {
    const res = await fetch("/api/suite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    if (!res.ok) return;
    const data = await res.json();
    syncSuiteChips(data.suite);
    state.selectedId = null;
    await loadTickets();
    el("stack-detail").textContent =
      mode === "full"
        ? `Full catalog — ${data.suite.active_total} tickets in the list.`
        : `Demo mode — ${data.suite.active_total} core tickets. Click Full 1000 to see all.`;
  }

  function renderTicketList() {
    const list = el("ticket-list");
    list.innerHTML = "";
    if (!state.tickets.length) {
      list.innerHTML = `<li class="empty">No tickets match.</li>`;
      return;
    }
    for (const t of state.tickets) {
      const li = document.createElement("li");
      li.className = t.id === state.selectedId ? "selected" : "";
      li.innerHTML = `
        <span class="tid">${t.id}</span>
        <span class="split">${t.split === "improve" ? "learn" : "hold"} · ${t.intent}</span>
        <p class="preview">${t.preview}</p>`;
      li.onclick = () => selectTicket(t.id);
      list.appendChild(li);
    }
  }

  async function selectTicket(id) {
    state.selectedId = id;
    setTeach("pick");
    renderTicketList();
    el("btn-run").disabled = state.busy || !id;
    const res = await fetch(`/api/tickets/${encodeURIComponent(id)}`);
    if (!res.ok) return;
    const data = await res.json();
    state.selected = data;
    const t = data.ticket;
    const e = data.expected || {};
    el("sel-id").textContent = t.id;
    el("sel-meta").textContent = `${t.split} · ${t.intent}${e.action ? ` · want ${e.action}` : ""}`;
    el("sel-message").textContent = t.message;
    el("sel-action").textContent = e.action || "—";
    el("sel-notes").textContent = e.notes || "—";
    el("ticket").textContent = t.id;
    el("result-line").textContent = "Ready — press ② Run.";
    el("result-line").className = "result-line";
    el("llm-draft").textContent = "Run the loop to see Qwen’s reply here.";
    const rl = el("reflect-lesson");
    if (rl) rl.textContent = "Autonomous lessons from learn-set tickets show here.";
    renderHealTimeline([]);
    setHealingPulse(false);
    setNodeBody("heal", "Ask LLM to rewrite");
    setTeach("pick");
    setGuide(
      `① Selected ${t.id} — press the orange button`,
      "Qwen will write a support reply. The checklist (not the LLM) decides pass/fail."
    );
  }

  function setHealStatus(text) {
    const n = el("heal-status");
    if (n) n.textContent = text;
  }

  function openRailPanel(id) {
    const panel = el(id);
    if (panel) panel.open = true;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function setHealingPulse(on) {
    const node = document.querySelector('.node[data-node="heal"]');
    if (node) node.classList.toggle("healing", !!on);
  }

  function renderHealTimeline(attempts, opts) {
    const ol = el("heal-timeline");
    ol.innerHTML = "";
    const list = attempts || [];
    if (!list.length) {
      ol.innerHTML = `<li class="empty">No attempts yet — run the loop.</li>`;
      setHealStatus("If the checklist fails, Heal retries (up to 2). Expand to read every draft.");
      setHealingPulse(false);
      return;
    }
    openRailPanel("panel-heal");
    const healsUsed = list.filter((a) => (a.heal_count_before || 0) > 0).length;
    const last = list[list.length - 1];
    const pending = opts && opts.willHeal;
    setHealStatus(
      pending
        ? `FAIL on attempt ${last.attempt} — Heal is retrying… (${list.length} so far)`
        : last.passed
          ? `PASS after ${list.length} attempt(s)${healsUsed ? ` · ${healsUsed} heal rewrite(s)` : " · no heal needed"}`
          : `Still FAIL after ${list.length} attempt(s)${healsUsed ? ` · ${healsUsed} heal(s) used` : ""} · max heals`
    );
    setHealingPulse(!!pending);
    for (const a of list) {
      const li = document.createElement("li");
      li.className = a.passed ? "pass" : "fail";
      const afterHeal = (a.heal_count_before || 0) > 0;
      const label = afterHeal
        ? `Attempt ${a.attempt} · after heal #${a.heal_count_before}`
        : `Attempt ${a.attempt} · first draft`;
      const miss = (a.missing || []).length ? `missing: ${(a.missing || []).join(", ")}` : "";
      const forbid = (a.forbidden_hits || []).length
        ? `forbidden: ${(a.forbidden_hits || []).join(", ")}`
        : "";
      const why = [a.details, miss, forbid].filter(Boolean).join(" · ");
      const draft = a.draft || "";
      const preview = draft.length > 120 ? `${draft.slice(0, 120)}…` : draft;
      li.innerHTML = `
        <details class="attempt-panel" ${a === last ? "open" : ""}>
          <summary class="attempt-summary">
            <span class="ht-head">
              <span>${escapeHtml(label)}</span>
              <span class="${a.passed ? "ok" : "bad"}">${a.passed ? "PASS" : "FAIL"}</span>
            </span>
            <span class="attempt-preview">${escapeHtml(preview || "—")}</span>
          </summary>
          <div class="attempt-body">
            <div>action ${escapeHtml(a.detected_action || "?")} → want ${escapeHtml(a.expected_action || "?")}</div>
            <div class="attempt-why">${escapeHtml(why || "—")}</div>
            <pre class="ht-draft expanded">${escapeHtml(draft)}</pre>
          </div>
        </details>`;
      ol.appendChild(li);
    }
    if (pending) {
      const li = document.createElement("li");
      li.className = "pending";
      li.innerHTML = `<div class="ht-head"><span>Heal queued</span><span class="warn">rewriting…</span></div>
        <div>Harness will re-retrieve → LLM rewrites with the error hint → checklist again.</div>`;
      ol.appendChild(li);
    }
  }

  function renderActivity(events) {
    state.events = events || [];
    const feed = el("activity");
    feed.innerHTML = "";
    if (!state.events.length) {
      feed.innerHTML = `<li class="empty">Live loop events appear here.</li>`;
      return;
    }
    for (const ev of state.events.slice(0, 60)) {
      const li = document.createElement("li");
      li.className =
        ev.passed === true || ev.kept === true
          ? "pass"
          : ev.passed === false || ev.kept === false
            ? "fail"
            : "";
      const when = (ev.ts || "").replace("T", " ").slice(11, 19);
      li.innerHTML = `<span class="when">${when}</span><span class="tag">[${ev.kind || "event"}]</span>${ev.detail || ev.status || ""}`;
      feed.appendChild(li);
    }
  }

  function pushLiveActivity(ev) {
    if (!ev || ev.type === "ping" || ev.type === "snapshot" || ev.type === "suite_ticket") return;
    if (ev.type === "step" && ev.node !== "heal" && ev.node !== "reflect") return;
    const detail =
      ev.type === "ticket_eval"
        ? `${ev.ticket_id || "?"} attempt ${(ev.attempt && ev.attempt.attempt) || "?"} → ${ev.passed ? "PASS" : "FAIL"}`
        : ev.stack_detail || ev.status || ev.ticket_id || "";
    state.events = [
      {
        ts: new Date().toISOString(),
        kind: ev.type || ev.status || "event",
        detail,
        passed: ev.passed,
        kept: ev.kept,
      },
      ...state.events,
    ].slice(0, 250);
    renderActivity(state.events);
  }

  function renderBeforeAfter(ba) {
    const deltaWrap = el("ba-delta").closest(".ba-col");
    const why = el("why-text");
    if (!ba) {
      el("ba-before").textContent = "—";
      el("ba-after").textContent = "—";
      el("ba-delta").textContent = "—";
      el("journey-meta").textContent = "Score the suite, then Learn — same loop on many tickets.";
      if (why) {
        why.textContent =
          "Score suite, then Learn — kept lessons and Learn/Holdout deltas show here as the reason for lift.";
      }
      deltaWrap.classList.remove("down", "flat");
      return;
    }
    el("ba-before").textContent = `A ${fmt(ba.before.part_a_rate)} · B ${fmt(ba.before.part_b_rate)}`;
    el("ba-after").textContent = `A ${fmt(ba.after.part_a_rate)} · B ${fmt(ba.after.part_b_rate)}`;
    el("ba-delta").textContent = `${fmtDelta(ba.delta_a)} / ${fmtDelta(ba.delta_b)}`;
    el("ba-before-detail").textContent = `Round ${ba.before.round}`;
    el("ba-after-detail").textContent = `Round ${ba.after.round}`;
    el("journey-meta").textContent = `${ba.rounds} rounds · ${ba.kept_count} kept · ${ba.reverted_count} reverted`;
    deltaWrap.classList.toggle("down", ba.delta_a < 0 || ba.delta_b < -0.01);
    deltaWrap.classList.toggle("flat", Math.abs(ba.delta_a) < 0.005 && Math.abs(ba.delta_b) < 0.005);
    if (why) why.textContent = ba.why || ba.after.lesson_summary || "—";
  }

  function renderJourney(milestones) {
    const ol = el("journey-timeline");
    ol.innerHTML = "";
    if (!milestones || !milestones.length) {
      ol.innerHTML = `<li class="empty">Suite scores appear after Score suite / Learn.</li>`;
      return;
    }
    for (const m of milestones) {
      const li = document.createElement("li");
      li.classList.toggle("start", !!m.is_start);
      li.classList.toggle("now", !!m.is_now);
      const gate = m.is_start ? "start" : m.kept ? "kept" : "reverted";
      li.innerHTML = `
        <div class="j-label">${m.label}</div>
        <div class="j-scores">A ${fmt(m.part_a_rate)} <span class="d">${fmtDelta(m.delta_a)}</span>
          · B ${fmt(m.part_b_rate)} <span class="d">${fmtDelta(m.delta_b)}</span></div>
        <div class="j-meta"><span class="${m.kept ? "kept-yes" : "kept-no"}">${gate}</span> · ${(m.lesson_summary || "").slice(0, 80)}</div>`;
      ol.appendChild(li);
    }
  }

  function renderHistory(rows) {
    state.history = rows || [];
    const body = el("history-body");
    body.innerHTML = "";
    if (!state.history.length) {
      body.innerHTML = `<tr><td colspan="9" class="empty-row">No suite rounds yet.</td></tr>`;
    } else {
      for (const r of state.history) {
        const tr = document.createElement("tr");
        tr.className = r.kept ? "row-kept" : "row-reverted";
        tr.innerHTML = `
          <td>${r.round}</td>
          <td>${fmt(r.part_a_rate)}</td>
          <td>${fmtDelta(r.delta_a)}</td>
          <td>${fmt(r.part_b_rate)}</td>
          <td>${fmtDelta(r.delta_b)}</td>
          <td class="${r.kept ? "kept-yes" : "kept-no"}">${r.kept ? "kept" : "reverted"}</td>
          <td>${r.prompt_version || ""}</td>
          <td>${(r.lesson_summary || "").slice(0, 120)}</td>
          <td>${(r.timestamp || "").replace("T", " ").slice(0, 19)}</td>`;
        body.appendChild(tr);
      }
    }
    chart.data.labels = state.history.map((r, i) =>
      i === 0 ? "was" : i === state.history.length - 1 ? "now" : `R${r.round}`
    );
    chart.data.datasets[0].data = state.history.map((r) => r.part_a_rate);
    chart.data.datasets[1].data = state.history.map((r) => r.part_b_rate);
    chart.update();
  }

  function renderLangfuse(lf) {
    if (!lf) return;
    const pill = el("lf-pill");
    if (pill) {
      const on = lf.enabled && lf.auth_ok;
      pill.textContent = `LangFuse · ${on ? "on" : lf.enabled ? "auth?" : "off"}`;
      pill.classList.toggle("on", !!on);
      pill.classList.toggle("off", !on);
    }
    const openBtn = el("btn-langfuse");
    if (openBtn && lf.ui_url) openBtn.href = lf.ui_url;
  }

  function setInspectorLink(url) {
    const wrap = el("lf-inspector-link-wrap");
    const link = el("lf-inspector-link");
    if (!wrap || !link) return;
    if (url) {
      wrap.hidden = false;
      link.href = url;
    } else wrap.hidden = true;
  }

  function applyEvent(ev) {
    if (!ev || ev.type === "ping") return;
    if (ev.node) highlightNode(ev.node);
    if (ev.stack_detail) el("stack-detail").textContent = ev.stack_detail;
    if (ev.ticket_id) el("ticket").textContent = ev.ticket_id;
    if (ev.status) el("status").textContent = ev.status;
    if (ev.part_a_rate != null) el("score-a").textContent = fmt(ev.part_a_rate);
    if (ev.part_b_rate != null) el("score-b").textContent = fmt(ev.part_b_rate);
    if (ev.round != null) el("score-round").textContent = String(ev.round);

    if (ev.node === "retrieve") setNodeBody("retrieve", "Fetching policy / FAQ…");
    if (ev.node === "generate") setNodeBody("generate", "Qwen drafting…");
    if (ev.node === "heal") setNodeBody("heal", "Retrying from checklist…");
    if (ev.node === "reflect" || (ev.status && String(ev.status).includes("improve_round"))) {
      highlightNode("reflect");
      setNodeBody("reflect", ev.stack_detail || "Writing lessons…");
      setTeach(ev.stack === "autonomous" ? "done" : "learn");
    }
    if (ev.node === "suite") {
      highlightNode("suite");
      setNodeBody("suite", ev.stack_detail || "Re-scoring suite…");
    }
    if (ev.type === "gate") {
      highlightNode(ev.stack === "autonomous" ? "reflect" : "gate");
      if (ev.stack === "autonomous") {
        setNodeBody("reflect", ev.stack_detail || (ev.kept ? "Lesson KEPT" : "Skipped"));
      } else {
        setNodeBody("gate", ev.stack_detail || (ev.kept ? "KEEP" : "REVERT"));
      }
      if (ev.inspector && ev.inspector.lesson) {
        const box = el("reflect-lesson");
        if (box) box.textContent = ev.inspector.lesson;
        openRailPanel("panel-reflect");
      }
    }

    if (ev.inspector && ev.inspector.autonomous_lesson) {
      const box = el("reflect-lesson");
      if (box) box.textContent = ev.inspector.autonomous_lesson;
      setNodeBody("reflect", "Lesson written → learnings.md");
      openRailPanel("panel-reflect");
    }

    if (ev.type === "ticket_eval") {
      const willHeal = !!ev.will_heal;
      setNodeBody(
        "evaluate",
        ev.passed ? "PASS" : willHeal ? "FAIL · healing next" : "FAIL · no more heals"
      );
      el("result-line").textContent = willHeal
        ? `${ev.ticket_id}: FAIL — healing…`
        : `${ev.ticket_id}: ${ev.passed ? "PASS" : "FAIL"}`;
      el("result-line").className = `result-line ${ev.passed ? "pass" : "fail"}`;
      if (ev.attempts) renderHealTimeline(ev.attempts, { willHeal });
      else if (ev.attempt) renderHealTimeline([ev.attempt], { willHeal });
      if (ev.attempt && ev.attempt.draft) {
        el("llm-draft").textContent = ev.attempt.draft;
        openRailPanel("panel-draft");
      }
      if (willHeal) {
        highlightNode("heal");
        setNodeBody("heal", "Queued — LLM will rewrite with checklist errors");
      } else if (!ev.passed) {
        setHealingPulse(false);
        setNodeBody("heal", "Stopped (max heals or final FAIL)");
      } else {
        setHealingPulse(false);
      }
    }
    if (ev.node === "heal" && ev.attempt_summary) {
      setHealingPulse(true);
      const miss = (ev.attempt_summary.missing || []).join(", ");
      const body = miss
        ? `Heal #${ev.heal_count || "?"}: fix ${miss}`
        : `Heal #${ev.heal_count || "?"}: ${ev.attempt_summary.reason || ""}`;
      setNodeBody("heal", body.slice(0, 140));
      setHealStatus(
        `Structured heal #${ev.heal_count || "?"} — prior draft + fix list sent to Generate`
      );
    }

    if (ev.langfuse_url) setInspectorLink(ev.langfuse_url);
    if (ev.inspector) {
      el("inspector").textContent = JSON.stringify(ev.inspector, null, 2);
      if (ev.inspector.langfuse_url) setInspectorLink(ev.inspector.langfuse_url);
      if (ev.inspector.draft) {
        el("llm-draft").textContent = ev.inspector.draft;
        setNodeBody("generate", String(ev.inspector.draft).slice(0, 120));
        openRailPanel("panel-draft");
      }
      if (ev.inspector.retrieved) {
        const docs = ev.inspector.retrieved;
        setNodeBody("retrieve", Array.isArray(docs) ? `${docs.length} chunks` : "retrieved");
      }
      if (ev.inspector.checklist && ev.type !== "ticket_eval") {
        const c = ev.inspector.checklist;
        const why = c.passed ? "PASS" : String(c.details || "FAIL").replace(/\s+/g, " ").slice(0, 72);
        setNodeBody("evaluate", c.passed ? "PASS" : `FAIL · ${why}`);
      }
      // Don't overwrite heal node with "0 heal(s)" while a retry is queued
      if (ev.inspector.heal_count != null && !ev.will_heal && ev.node !== "heal") {
        const n = Number(ev.inspector.heal_count) || 0;
        if (n > 0) setNodeBody("heal", `${n} heal rewrite(s) used`);
      }
    }

    pushLiveActivity(ev);
    if (ev.type === "round" || ev.type === "gate" || ev.status === "baseline_done" || ev.status === "improve_done") {
      refreshHistory();
      setTeach("learn");
      if (ev.status === "improve_done" || ev.type === "gate") loadKnowledge();
    }
    if (
      ev.status === "baseline_done" ||
      ev.status === "improve_done" ||
      ev.status === "demo_done" ||
      ev.status === "error" ||
      ev.status === "reset"
    ) {
      setBusy(false, ev.status === "error" ? "error" : "idle");
      if (ev.status === "demo_done") {
        setTeach("done");
        refreshLangfuse();
        if (ev.inspector && (ev.inspector.autonomous_lesson || ev.inspector.autonomous)) {
          loadKnowledge();
        }
      }
      if (ev.status === "baseline_done") {
        setGuide(
          "③ Suite scored — next: Learn",
          "Where it was is filled. Press “Learn + keep/revert” so Reflect (LLM) writes lessons if the gate allows."
        );
      }
      if (ev.status === "improve_done") {
        setGuide(
          "④ Learn finished — check lift",
          "Compare where it was → where it is now. Expand Memory to see learnings.md."
        );
        loadKnowledge();
      }
      if (ev.status === "reset") {
        renderHistory([]);
        renderBeforeAfter(null);
        renderJourney([]);
        renderActivity([]);
        el("llm-draft").textContent = "Run the loop to see Qwen’s reply here.";
        setTeach("pick");
      }
    }
    if (ev.type === "error") el("inspector").textContent = ev.message || "error";
  }

  async function refreshLangfuse() {
    try {
      renderLangfuse(await (await fetch("/api/langfuse")).json());
    } catch (_) {}
  }

  async function refreshHistory() {
    const data = await (await fetch("/api/history")).json();
    renderHistory(data.rounds || []);
    renderBeforeAfter(data.before_after);
    renderJourney(data.journey || []);
    if (data.events) renderActivity(data.events);
  }

  async function refreshState() {
    const data = await (await fetch("/api/state")).json();
    applyEvent({ type: "snapshot", ...data.snapshot });
    renderHistory(data.history || []);
    renderBeforeAfter(data.before_after);
    renderJourney(data.journey || []);
    renderActivity(data.events || []);
    renderLangfuse(data.langfuse);
    if (data.suite) {
      syncSuiteChips(data.suite);
    }
    setBusy(!!data.busy, data.busy ? "busy" : "idle");
  }

  async function post(url, body) {
    state.seenNodes = new Set();
    document.querySelectorAll(".node").forEach((d) => d.classList.remove("active", "done"));
    el("stack-detail").textContent = "Loop running…";
    setBusy(true, "starting");
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : "{}",
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      setBusy(false, "error");
      alert(err.error || res.statusText);
    }
  }

  document.querySelectorAll("[data-suite]").forEach((c) => {
    c.onclick = () => {
      if (state.busy) return;
      setSuiteMode(c.dataset.suite);
    };
  });
  document.querySelectorAll("[data-split]").forEach((c) => {
    c.onclick = () => {
      document.querySelectorAll("[data-split]").forEach((x) => x.classList.remove("active"));
      c.classList.add("active");
      state.split = c.dataset.split || "";
      loadTickets();
    };
  });
  let searchTimer;
  el("ticket-search").oninput = (e) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      state.query = e.target.value.trim();
      loadTickets();
    }, 180);
  };

  el("btn-run").onclick = () => {
    if (!state.selectedId) return;
    setTeach("run");
    post("/api/run-ticket", { ticket_id: state.selectedId });
  };
  function openScorePanel() {
    const bar = el("score-bar");
    if (bar) bar.open = true;
    requestAnimationFrame(() => chart.resize());
  }

  el("btn-baseline").onclick = () => {
    setTeach("learn");
    setGuide("③ Scoring the suite…", "Running the same loop on many tickets. This can take a while on local Qwen.");
    openScorePanel();
    post("/api/baseline");
  };
  el("btn-improve").onclick = () => {
    setTeach("learn");
    setGuide("④ Learning…", "Reflect (LLM) writes lessons from learn-set failures; gate may keep or revert.");
    openScorePanel();
    post("/api/improve", { rounds: Number(el("rounds").value || 1) });
  };
  el("btn-reset").onclick = async () => {
    await post("/api/reset");
    await refreshState();
    await loadKnowledge();
  };

  const scoreBar = el("score-bar");
  if (scoreBar) {
    scoreBar.addEventListener("toggle", () => {
      if (scoreBar.open) requestAnimationFrame(() => chart.resize());
    });
  }

  const es = new EventSource("/api/events");
  es.onmessage = (msg) => {
    try {
      applyEvent(JSON.parse(msg.data));
    } catch (_) {}
  };

  function renderKnowledge(data) {
    if (!data) return;
    const stack = el("stack-list");
    stack.innerHTML = "";
    for (const s of data.stack || []) {
      const li = document.createElement("li");
      li.innerHTML = `<strong>${s.name}</strong><div class="role">${s.role}</div><div class="detail">${s.detail || ""}</div>`;
      stack.appendChild(li);
    }
    const splits = data.splits || {};
    const learn = splits.learn_set || {};
    const hold = splits.holdout || {};
    el("splits-box").innerHTML = `
      <div class="split-card">
        <h3>${learn.name || "Learn set"}</h3>
        <p><strong>${learn.count_catalog ?? "—"}</strong> tickets (active ${learn.count_active ?? "—"})</p>
        <p class="role">Used for: ${learn.used_for || ""}</p>
      </div>
      <div class="split-card">
        <h3>${hold.name || "Holdout"}</h3>
        <p><strong>${hold.count_catalog ?? "—"}</strong> tickets (active ${hold.count_active ?? "—"})</p>
        <p class="role">Used for: ${hold.used_for || ""}</p>
        <p class="role">Not used for: ${hold.not_used_for || ""}</p>
      </div>
      <div class="rag-note">${splits.rag_note || ""}</div>`;
    el("policy-text").textContent = (data.policy && data.policy.text) || "(missing policy.md)";
    const faq = el("faq-list");
    faq.innerHTML = "";
    for (const f of data.faqs || []) {
      const d = document.createElement("details");
      d.innerHTML = `<summary>${f.name}</summary><pre>${f.text}</pre>`;
      faq.appendChild(d);
    }
    el("prompt-text").textContent = data.prompt || "(empty)";
    el("learnings-text").textContent = data.learnings || "(none yet)";
  }

  async function loadKnowledge() {
    try {
      renderKnowledge(await (await fetch("/api/knowledge")).json());
    } catch (_) {}
  }

  document.querySelectorAll(".ktab").forEach((btn) => {
    btn.onclick = () => {
      document.querySelectorAll(".ktab").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".ktab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = el(`ktab-${btn.dataset.ktab}`);
      if (panel) panel.classList.add("active");
      if (btn.dataset.ktab === "memory") loadKnowledge();
    };
  });

  setTeach("pick");
  loadTickets();
  loadKnowledge();
  refreshState();
})();
