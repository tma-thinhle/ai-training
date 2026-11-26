// Live Server serves the frontend; FastAPI runs separately.
const API_BASE = (new URLSearchParams(location.search).get("api") || "http://127.0.0.1:8002").replace(/\/$/, "");
const $ = (id) => document.getElementById(id);
let cases = [];
let busy = false;
let connected = false;
let currentRun = "";
let report = null;
let liveResults = [];
const observedErrors = new Set();

function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}

function message(text = "") {
  $("message").textContent = text;
  $("message").hidden = !text;
}

async function api(path, options = {}) {
  const response = await fetch(API_BASE + path, options);
  return { status: response.status, ok: response.ok, data: await response.json() };
}

async function data(path, options) {
  const result = await api(path, options);
  if (!result.ok) throw new Error([result.data.detail, ...(result.data.errors || [])].join(" "));
  return result.data;
}

function post(body, headers = {}) {
  return { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body) };
}

function isCustom() { return $("dataset").value === "custom"; }

function setBusy(value) {
  busy = value;
  for (const id of ["dataset", "run", "refresh", "saved-run"]) $(id).disabled = value || !connected;
  $("case").disabled = value || !connected || isCustom();
  $("request-field").disabled = value || !connected || !isCustom();
  $("meeting-text").disabled = value || !connected;
  $("reconnect").disabled = value;
  $("evaluate-current").disabled = value || !currentRun;
  $("evaluate-report").disabled = value || !$("saved-run").value;
}

function showConfiguration(config) {
  const settings = config.settings;
  $("configuration").replaceChildren();
  for (const [label, value] of [["Model", config.model], ["Reasoning", settings.reasoning_effort],
    ["Output tokens", settings.max_output_tokens], ["Timeout", `${settings.timeout_seconds}s`], ["Retries", settings.max_retries]]) {
    const row = element("div");
    row.append(element("dt", label), element("dd", String(value)));
    $("configuration").append(row);
  }
  $("prompt").textContent = config.prompt;
}

function renderCriteria() {
  $("criterion-api").textContent = connected ? "Available" : "Unavailable";
  const successes = report ? report.predictions.filter((item) => item.status === "ok").length : liveResults.filter((item) => item.ok).length;
  $("criterion-schema").textContent = successes ? `${successes}/${successes} · 100%` : "—";
  const fullOriginal = report?.case_ids.length === 20 && report.case_ids.every((id) => /^TC\d{2}$/.test(id));
  $("criterion-f1").textContent = fullOriginal ? (report.summary?.f1 || "Pending") : "—";
  $("error-observations").replaceChildren();
  for (const [key, label] of [["invalid", "422"], ["timeout", "Timeout"], ["rate_limit", "429"], ["server_error", "500"], ["malformed", "Malformed"]]) {
    const seen = observedErrors.has(key);
    const badge = element("span", `${label} ${seen ? "✓" : "—"}`, seen ? "badge good" : "badge");
    badge.title = seen ? "Observed" : "Not observed";
    $("error-observations").append(badge);
  }
}

function observe(result) {
  liveResults.push(result);
  if (result.status === 422) observedErrors.add("invalid");
  if (result.data.error_type === "timeout") observedErrors.add("timeout");
  if (result.data.upstream_status === 429) observedErrors.add("rate_limit");
  if (result.data.upstream_status === 500) observedErrors.add("server_error");
  if (result.data.error_type === "invalid_output") observedErrors.add("malformed");
  renderCriteria();
}

function preview(item) {
  $("meeting-text").value = item ? item.input : "";
  $("preview-label").textContent = item ? item.id : "";
}

function selectionChanged() {
  const selected = cases.find((item) => item.id === $("case").value);
  preview(selected || cases[0]);
  $("run").textContent = selected ? `Run ${selected.id} · paid` : `Run all ${cases.length} · paid`;
}

async function loadDataset() {
  setBusy(true);
  const custom = isCustom();
  $("case-label").hidden = custom;
  $("request-field-label").hidden = !custom;
  $("meeting-text").readOnly = !custom;
  if (custom) {
    cases = [];
    preview(null);
    $("case-count").textContent = "Custom";
    $("run").textContent = "Run · paid";
  } else {
    cases = await data(`/demo/datasets/${encodeURIComponent($("dataset").value)}`);
    $("case").replaceChildren(new Option(`All ${cases.length}`, ""));
    for (const item of cases) $("case").add(new Option(`${item.id} · ${item.title}`, item.id));
    $("case-count").textContent = `${cases.length} cases`;
    selectionChanged();
  }
  setBusy(false);
}

async function connect() {
  message(); setBusy(true);
  try {
    showConfiguration(await data("/demo/config"));
    await data("/openapi.json");
    $("docs").href = API_BASE + "/docs";
    const datasets = await data("/demo/datasets");
    $("dataset").replaceChildren();
    for (const item of datasets) $("dataset").add(new Option(item.label, item.id));
    $("dataset").add(new Option("Custom", "custom"));
    await loadDataset();
    connected = true;
    $("connection").textContent = "Connected";
    $("connection").className = "badge good";
  } catch (error) {
    connected = false;
    $("connection").textContent = "Disconnected";
    $("connection").className = "badge bad";
    message(`Cannot connect to ${API_BASE}. ${error.message}`);
  }
  setBusy(false); renderCriteria();
}

function outputView(target, caseId, result, body) {
  target.replaceChildren();
  const section = element("div", undefined, "output-section");
  const heading = element("div", undefined, "card-heading");
  heading.append(element("h3", caseId), element("span", `HTTP ${result.status}`, result.ok ? "badge good" : "badge bad"));
  section.append(heading);
  if (result.ok) {
    section.append(element("h4", "Summary"), element("p", result.data.summary), element("h4", "Decisions"));
    const list = element("ul");
    for (const decision of result.data.decisions) list.append(element("li", decision));
    section.append(result.data.decisions.length ? list : element("p", "—"));
    section.append(element("h4", "Actions"));
    if (result.data.actions.length) {
      const table = element("table");
      const head = element("tr");
      for (const name of ["Owner", "Action", "Due date"]) head.append(element("th", name));
      const thead = element("thead"); thead.append(head); table.append(thead);
      const tbody = element("tbody");
      for (const action of result.data.actions) {
        const row = element("tr");
        for (const value of [action.owner ?? "—", action.action, action.due_date ?? "—"]) row.append(element("td", value));
        tbody.append(row);
      }
      table.append(tbody);
      const wrapper = element("div", undefined, "table-wrap"); wrapper.append(table); section.append(wrapper);
    } else section.append(element("p", "—"));
  } else {
    if (result.data.upstream_status) section.append(element("span", `Upstream ${result.data.upstream_status}`, "badge bad"));
    section.append(element("p", result.data.detail));
    const list = element("ul");
    for (const error of result.data.errors || []) list.append(element("li", error));
    section.append(list);
  }
  for (const [label, value] of [["Request JSON", body], ["Response JSON", result.data]]) {
    const raw = element("details"); raw.append(element("summary", label), element("pre", JSON.stringify(value, null, 2))); section.append(raw);
  }
  target.append(section);
}

async function runSelection(event) {
  event.preventDefault();
  if (busy) return;
  if (isCustom() && (!$("request-field").value.trim() || !$("meeting-text").value.trim())) {
    message("Fill in the request field and meeting notes."); return;
  }
  setBusy(true); message();
  report = null; liveResults = []; currentRun = "";
  $("run-results").hidden = false; $("evaluate-current").hidden = true;
  $("case-results").replaceChildren(); $("output").replaceChildren();
  $("run-folder").textContent = "";
  $("progress").textContent = "Running";
  try {
    if (isCustom()) {
      showConfiguration(await data("/demo/config"));
      const body = { [$("request-field").value.trim()]: $("meeting-text").value };
      const result = await api("/analyze-meeting", post(body));
      observe(result); outputView($("output"), "Custom", result, body);
      $("progress").textContent = "Finished";
    } else {
      const run = await data("/demo/runs", post({ dataset: $("dataset").value, case_id: $("case").value || null }));
      currentRun = run.run_id;
      showConfiguration(run);
      $("run-folder").textContent = run.run_id;
      for (const [index, item] of run.cases.entries()) {
        preview(item);
        $("progress").textContent = `${index + 1}/${run.cases.length} · ${item.id}`;
        const body = { meeting_text: item.input };
        const result = await api("/analyze-meeting", post(body, { "X-Run-ID": run.run_id, "X-Case-ID": item.id }));
        observe(result);
        const button = element("button", `${item.id} · ${result.status}`, result.ok ? "ok" : "failed");
        button.addEventListener("click", () => { preview(item); outputView($("output"), item.id, result, body); });
        $("case-results").append(button);
        outputView($("output"), item.id, result, body);
      }
      $("progress").textContent = `${run.cases.length}/${run.cases.length}`;
      $("evaluate-current").hidden = false;
    }
  } catch (error) {
    $("progress").textContent = "Stopped"; message(error.message);
  } finally { setBusy(false); renderCriteria(); }
}

async function refreshReports(selectedRun) {
  message();
  try {
    const previous = selectedRun || $("saved-run").value || currentRun;
    const runs = await data("/demo/runs");
    $("saved-run").replaceChildren(new Option("Select a run", ""));
    for (const run of runs) $("saved-run").add(new Option(`${run.run_id} · ${run.completed}/${run.selected} · ${run.evaluated ? "evaluated" : "pending"}`, run.run_id));
    if (runs.some((run) => run.run_id === previous)) $("saved-run").value = previous;
    await loadReport();
  } catch (error) { message(error.message); }
}

function renderComparisons() {
  $("comparisons").replaceChildren();
  if (!report) return;
  const rows = report.comparisons.filter((row) => (!$("report-case").value || row.case_id === $("report-case").value) &&
    (!$("issues-only").checked || !["Correct", "Correctly empty"].includes(row.result)));
  for (const item of rows) {
    const row = element("tr");
    for (const key of ["case_id", "item", "golden", "prediction", "result", "reason"]) {
      const cell = element("td");
      if (key === "result") cell.append(element("span", item.result, ["Correct", "Correctly empty"].includes(item.result) ? "badge good" : "badge bad"));
      else cell.textContent = item[key] || "—";
      row.append(cell);
    }
    $("comparisons").append(row);
  }
}

async function loadReport() {
  const runId = $("saved-run").value;
  $("report-content").hidden = !runId;
  if (!runId) { report = null; renderCriteria(); setBusy(busy); return; }
  const loaded = await data(`/demo/runs/${encodeURIComponent(runId)}`);
  if ($("saved-run").value !== runId) return;
  report = loaded;
  const summary = report.summary;
  $("report-status").textContent = summary ? `${summary.status} · model judged` : "Not evaluated";
  $("report-status").className = summary?.status === "complete" ? "badge good" : "badge";
  $("saved-config").textContent = `${report.model}\n${JSON.stringify(report.settings, null, 2)}\n\n${report.prompt}`;
  $("summary-cards").replaceChildren();
  $("summary-detail").textContent = summary ? `${summary.summaries_needing_review} summary issues · ${summary.extraction_failures} extraction failures · ${summary.judge_errors} judge errors` : `${report.predictions.length}/${report.case_ids.length} saved`;
  if (summary) for (const [label, value] of [["F1", summary.f1 || (summary.status === "incomplete" ? "Pending" : "—")], ["Correct", summary.correct], ["Extra", summary.extra], ["Missed", summary.missed]]) {
    const card = element("div", undefined, "stat"); card.append(element("span", label), element("strong", value)); $("summary-cards").append(card);
  }
  $("downloads").replaceChildren();
  for (const file of report.files) {
    const link = element("a", file); link.href = `${API_BASE}/demo/runs/${encodeURIComponent(runId)}/files/${file}`; $("downloads").append(link);
  }
  $("comparison-section").hidden = !report.comparisons.length;
  $("report-case").replaceChildren(new Option("All meetings", ""));
  for (const caseId of [...new Set(report.comparisons.map((row) => row.case_id))]) $("report-case").add(new Option(caseId, caseId));
  renderComparisons(); renderCriteria(); setBusy(busy);
  $("saved-predictions").replaceChildren();
  const details = element("details"); details.append(element("summary", "Extraction responses"));
  for (const prediction of report.predictions) {
    const box = element("details"); box.append(element("summary", `${prediction.case_id} · ${prediction.status}`), element("pre", JSON.stringify(prediction.analysis || { error: prediction.error, http_status: prediction.http_status, upstream_status: prediction.upstream_status }, null, 2))); details.append(box);
  }
  $("saved-predictions").append(details);
}

async function evaluateRun(runId) {
  if (busy || !runId) return;
  setBusy(true); message();
  const button = $("saved-run").value === runId && !$("reports-page").hidden ? $("evaluate-report") : $("evaluate-current");
  button.textContent = "Evaluating…";
  try {
    await data(`/demo/runs/${encodeURIComponent(runId)}/evaluate`, post({}));
    showPage("reports");
    await refreshReports(runId);
  } catch (error) { message(error.message); }
  finally {
    button.textContent = "Evaluate · paid"; setBusy(false);
  }
}

function showPage(name) {
  for (const page of ["run", "reports"]) {
    $(`${page}-page`).hidden = page !== name;
    $(`${page}-tab`).classList.toggle("active", page === name);
    $(`${page}-tab`).setAttribute("aria-selected", String(page === name));
  }
  document.body.dataset.page = name;
}

$("run-tab").addEventListener("click", () => showPage("run"));
$("reports-tab").addEventListener("click", () => { showPage("reports"); refreshReports(); });
$("reconnect").addEventListener("click", connect);
$("dataset").addEventListener("change", () => loadDataset().catch((error) => { setBusy(false); message(error.message); }));
$("case").addEventListener("change", selectionChanged);
$("meeting-form").addEventListener("submit", runSelection);
$("refresh").addEventListener("click", () => refreshReports());
$("saved-run").addEventListener("change", () => loadReport().catch((error) => message(error.message)));
$("evaluate-current").addEventListener("click", () => evaluateRun(currentRun));
$("evaluate-report").addEventListener("click", () => evaluateRun($("saved-run").value));
$("report-case").addEventListener("change", renderComparisons);
$("issues-only").addEventListener("change", renderComparisons);
renderCriteria(); connect();
