/*
 * Dashboard logic.
 * Tries the real backend first (http://localhost:8000). If it's not
 * running, falls back to bundled sample data so the dashboard is always
 * demoable on its own — useful when showing this to someone without
 * spinning up the backend first.
 */

const API_BASE = "http://localhost:8000/api";

const SAMPLE_MATCHES = [
  { job: { title: "Backend Engineer", company: "Northwind Systems" }, score: 0.61, recommended: true },
  { job: { title: "Data Engineer", company: "Northwind Systems" }, score: 0.44, recommended: true },
  { job: { title: "QA / Automation Engineer", company: "Verity Cloud" }, score: 0.31, recommended: false },
  { job: { title: "Machine Learning Intern", company: "Lumen Analytics" }, score: 0.22, recommended: false },
  { job: { title: "Frontend Developer", company: "Brightpath Labs" }, score: 0.09, recommended: false },
];

async function fetchMatches() {
  try {
    const res = await fetch(`${API_BASE}/jobs/match`);
    if (!res.ok) throw new Error("backend not ok");
    return await res.json();
  } catch (err) {
    return SAMPLE_MATCHES; // backend not running — use sample data
  }
}

function renderStats(matches) {
  const total = matches.length;
  const recommended = matches.filter(m => m.recommended).length;
  const avgScore = total ? (matches.reduce((s, m) => s + m.score, 0) / total) : 0;

  document.getElementById("statMatched").textContent = total;
  document.getElementById("statRecommended").textContent = recommended;
  document.getElementById("statApplied").textContent = 0; // real once agent layer exists
  document.getElementById("statAvgScore").textContent = avgScore.toFixed(2);

  document.getElementById("count-parsed").textContent = 1;
  document.getElementById("count-matched").textContent = total;
  document.getElementById("count-queued").textContent = recommended;
  document.getElementById("count-applied").textContent = 0;
  document.getElementById("count-review").textContent = recommended;

  // Highlight the furthest stage that currently has activity.
  const stages = ["parsed", "matched", "queued", "applied", "review"];
  const activeStage = recommended > 0 ? "queued" : "matched";
  document.querySelectorAll(".pipeline-stage").forEach(el => {
    el.classList.toggle("is-active", el.dataset.stage === activeStage);
  });
}

function renderTable(matches) {
  const body = document.getElementById("applicationsBody");
  if (!matches.length) {
    body.innerHTML = `<tr><td colspan="4" class="empty-row">No matches yet.</td></tr>`;
    return;
  }

  body.innerHTML = matches.map(m => `
    <tr>
      <td>${m.job.title}</td>
      <td>${m.job.company}</td>
      <td>${m.score.toFixed(2)}</td>
      <td>
        <span class="pill ${m.recommended ? "pill-recommended" : "pill-matched"}">
          ${m.recommended ? "recommended" : "matched"}
        </span>
      </td>
    </tr>
  `).join("");
}

function appendLog(message) {
  const log = document.getElementById("agentLog");
  const line = document.createElement("div");
  line.className = "log-line";
  const time = new Date().toLocaleTimeString([], { hour12: false });
  line.innerHTML = `<span>[${time}]</span> ${message}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function setAgentStatus(active) {
  document.getElementById("statusDot").classList.toggle("active", active);
  document.getElementById("statusText").textContent = active ? "Agent running" : "Agent idle";
}

async function init() {
  setAgentStatus(false);
  appendLog("Loading resume profile…");

  const matches = await fetchMatches();

  appendLog(`Parsed profile — ${matches.length ? "skills extracted" : "no skills found"}`);
  appendLog(`Scored ${matches.length} job postings against profile`);

  const recommended = matches.filter(m => m.recommended).length;
  appendLog(`${recommended} job(s) above match threshold — queued for review`);

  renderStats(matches);
  renderTable(matches);

  setAgentStatus(false);
  appendLog("Idle — browser automation layer not yet connected");
}

init();
