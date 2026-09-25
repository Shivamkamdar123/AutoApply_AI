/**
 * AutoApply AI — Autonomous Job Application Agent Dashboard
 * =========================================================
 * Connects to live FastAPI backend (http://localhost:8000/api) with
 * graceful offline fallback to local sample data for standalone demos.
 */

// Explicitly connect to 127.0.0.1:8000 for deterministic IPv4 compatibility on Windows
function resolveInitialApiBase() {
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.has("api")) {
    return urlParams.get("api");
  }
  return "http://127.0.0.1:8000/api";
}

let API_BASE = resolveInitialApiBase();
let isLiveApi = false;
let currentProfile = null;
let currentMatches = [];
let currentQueue = [];

// Fallback sample data for offline standalone mode
const SAMPLE_PROFILE = {
  full_name: "Alex Rivera",
  email: "alex.rivera@example.com",
  phone: "+1 (555) 789-0123",
  skills: ["python", "fastapi", "sql", "docker", "kubernetes", "git", "rest api", "postgresql"],
  years_experience: 4.5,
  language: "en",
};

const SAMPLE_MATCHES = [
  {
    job: {
      id: "job-001",
      title: "Senior Backend Engineer",
      company: "Northwind Systems",
      location: "Bengaluru, IN (Hybrid)",
      source: "greenhouse",
      description: "FastAPI, Python, Docker, SQL, REST APIs.",
    },
    score: 0.88,
    matched_skills: ["python", "fastapi", "docker", "sql", "git", "rest api"],
    recommended: true,
  },
  {
    job: {
      id: "job-005",
      title: "Data Platform Engineer",
      company: "Northwind Systems",
      location: "Bengaluru, IN",
      source: "lever",
      description: "Python, SQL, PostgreSQL, AWS data pipelines.",
    },
    score: 0.65,
    matched_skills: ["python", "sql", "postgresql", "git"],
    recommended: true,
  },
  {
    job: {
      id: "job-004",
      title: "QA / Automation Engineer",
      company: "Verity Cloud",
      location: "Remote",
      source: "sample",
      description: "Playwright, Docker, Python scripting.",
    },
    score: 0.42,
    matched_skills: ["docker", "python"],
    recommended: false,
  },
  {
    job: {
      id: "job-002",
      title: "Machine Learning Intern",
      company: "Lumen Analytics",
      location: "Remote",
      source: "sample",
      description: "PyTorch, scikit-learn, data pipelines.",
    },
    score: 0.28,
    matched_skills: ["python"],
    recommended: false,
  },
];

const SAMPLE_QUEUE = [
  {
    job_id: "job-001",
    company: "Northwind Systems",
    title: "Senior Backend Engineer",
    stage: "needs_review",
    match_score: 0.88,
    updated_at: new Date().toISOString(),
    dry_run: true,
    notes: "High match score (88%). Form fields auto-mapped.",
    field_mappings: [
      { field_name: "Full Name", selector: "input[name='name']", value_filled: "Alex Rivera", confidence: 0.98, source_field: "profile.full_name", rationale: "Extracted candidate name" },
      { field_name: "Email Address", selector: "input[type='email']", value_filled: "alex.rivera@example.com", confidence: 0.99, source_field: "profile.email", rationale: "Exact regex match" },
      { field_name: "Phone Number", selector: "input[type='tel']", value_filled: "+1 (555) 789-0123", confidence: 0.95, source_field: "profile.phone", rationale: "Normalized international format" },
      { field_name: "Years Experience", selector: "input[name='experience']", value_filled: "4.5", confidence: 0.90, source_field: "profile.years_experience", rationale: "Calculated date range span" },
    ],
  },
];

/* ---------- Network Helpers ---------- */

async function apiFetch(endpoint, options = {}) {
  const controller = new AbortController();
  // 30 second timeout allows multi-source job scraping and polite rate-limits to complete safely
  const timeoutId = setTimeout(() => controller.abort(), 30000);
  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timeoutId);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }
    return await res.json();
  } catch (err) {
    clearTimeout(timeoutId);
    console.error(`[AutoApply API Error] ${endpoint}:`, err);
    throw err;
  }
}

/* ---------- UI Logging & Notifications ---------- */

function appendLog(message, type = "info", correlationId = "sys") {
  const log = document.getElementById("agentLog");
  if (!log) return;
  const line = document.createElement("div");
  line.className = `log-line log-${type}`;
  const time = new Date().toLocaleTimeString([], { hour12: false });
  line.innerHTML = `<span class="log-time">[${time}]</span> <span class="log-corr">[${correlationId}]</span> ${message}`;
  log.appendChild(line);
  log.scrollTop = log.scrollHeight;
}

function showToast(message, type = "info") {
  const container = document.getElementById("toastContainer");
  if (!container) return;
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${type === "success" ? "✓" : type === "error" ? "⚠" : "ℹ"}</span> <span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

/* ---------- State Renderers ---------- */

function updateConnectionBadge(connected) {
  isLiveApi = connected;
  const badge = document.getElementById("connectionBadge");
  const banner = document.getElementById("connectionBanner");
  const bannerMsg = document.getElementById("bannerMessage");

  if (connected) {
    badge.className = "badge-tag connected";
    badge.textContent = "Live API Connected";
    banner.style.display = "none";
  } else {
    badge.className = "badge-tag standalone";
    badge.textContent = "Offline Demo Mode";
    banner.style.display = "flex";
    bannerMsg.textContent = "Backend offline (http://localhost:8000). Running in standalone demo mode with cached data.";
  }
}

function renderProfile(profile) {
  currentProfile = profile;
  document.getElementById("profileName").textContent = profile.full_name || "Anonymous Candidate";
  document.getElementById("profileExp").textContent = profile.years_experience ? `${profile.years_experience} yrs exp` : "Entry level";
  document.getElementById("profileLang").textContent = (profile.language || "EN").toUpperCase();
  document.getElementById("profileContact").textContent = `${profile.email || "No email"} • ${profile.phone || "No phone"}`;

  const initials = (profile.full_name || "AA").split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
  document.getElementById("profileAvatar").textContent = initials;

  const skillsContainer = document.getElementById("profileSkills");
  skillsContainer.innerHTML = (profile.skills || []).map(skill => `<span class="skill-chip">${skill}</span>`).join("");
}

function renderStats(matches, queue, summary = null) {
  const totalScored = (summary && summary.total_matched !== undefined) ? summary.total_matched : matches.length;
  const pendingReview = (summary && summary.total_needs_review !== undefined)
    ? summary.total_needs_review
    : queue.filter(q => q.stage === "needs_review").length;
  const appliedCount = (summary && summary.total_applied !== undefined)
    ? summary.total_applied
    : queue.filter(q => q.stage === "applied" || q.stage === "submitted").length;
  const avgScore = (summary && summary.average_match_score !== undefined)
    ? summary.average_match_score
    : (matches.length ? (matches.reduce((acc, m) => acc + m.score, 0) / matches.length) : 0);

  document.getElementById("statMatched").textContent = totalScored;
  document.getElementById("statRecommended").textContent = pendingReview;
  document.getElementById("statApplied").textContent = appliedCount;
  document.getElementById("statAvgScore").textContent = avgScore.toFixed(2);

  document.getElementById("count-parsed").textContent = 1;
  document.getElementById("count-matched").textContent = totalScored;
  document.getElementById("count-review").textContent = pendingReview;
  document.getElementById("count-applied").textContent = appliedCount;
  document.getElementById("count-submitted").textContent = summary ? (summary.total_submitted || 0) : 0;

  // Active track node
  const activeStage = pendingReview > 0 ? "review" : (appliedCount > 0 ? "applied" : "matched");
  document.querySelectorAll(".pipeline-stage").forEach(el => {
    el.classList.toggle("is-active", el.dataset.stage === activeStage);
  });
}

function renderReviewQueue(queue) {
  currentQueue = queue;
  const container = document.getElementById("reviewQueueList");
  const countLabel = document.getElementById("queuePendingCount");
  const pending = queue.filter(q => q.stage === "needs_review");

  countLabel.textContent = `${pending.length} pending review`;

  if (pending.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <span class="empty-state-icon">✨</span>
        <strong>Review Queue Clear</strong>
        <span>All drafted applications have been reviewed or no recommended matches found.</span>
      </div>
    `;
    return;
  }

  container.innerHTML = pending.map(item => `
    <div class="review-card" data-job-id="${item.job_id}">
      <div class="review-card-header">
        <div>
          <h3 class="review-job-title">${item.title}</h3>
          <div class="review-company-row">
            <span>🏢 <strong>${item.company}</strong></span>
            <span>•</span>
            <span>ID: ${item.job_id}</span>
          </div>
        </div>
        <div class="score-badge">
          <span>🎯</span>
          <span>${Math.round(item.match_score * 100)}% Match</span>
        </div>
      </div>

      <table class="review-fields-table">
        <thead>
          <tr>
            <th>Application Field</th>
            <th>Proposed Value</th>
            <th>Confidence</th>
            <th>Source / Rationale</th>
          </tr>
        </thead>
        <tbody>
          ${(item.field_mappings || []).map(f => `
            <tr>
              <td><strong>${f.field_name}</strong></td>
              <td>${f.value_filled}</td>
              <td><span class="confidence-meter">${Math.round(f.confidence * 100)}%</span></td>
              <td style="color: var(--text-muted);">${f.rationale}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>

      <div class="review-card-actions">
        <div class="review-notes">
          <span>🛡️ <strong>Safety Valve:</strong> Approving will execute form verification in Dry Run mode without submitting.</span>
        </div>
        <div class="action-buttons">
          <button class="btn btn-sm btn-danger" onclick="handleReviewAction('${item.job_id}', 'reject')">
            ✕ Reject
          </button>
          <button class="btn btn-sm btn-primary" onclick="handleReviewAction('${item.job_id}', 'approve')">
            ✓ Approve (Dry Run)
          </button>
        </div>
      </div>
    </div>
  `).join("");
}

function renderTable(matches) {
  currentMatches = matches;
  const body = document.getElementById("applicationsBody");
  if (!matches.length) {
    body.innerHTML = `<tr><td colspan="5" class="empty-row">No matching job postings found.</td></tr>`;
    return;
  }

  body.innerHTML = matches.map(m => `
    <tr>
      <td><strong>${m.job.title}</strong></td>
      <td>${m.job.company}</td>
      <td>
        <span style="font-family: var(--font-mono); font-weight: 600;">
          ${(m.score * 100).toFixed(0)}%
        </span>
      </td>
      <td>
        <span class="pill pill-source">${m.job.source || "sample"}</span>
      </td>
      <td>
        <span class="pill ${m.recommended ? "pill-recommended" : "pill-matched"}">
          ${m.recommended ? "★ Recommended" : "Matched"}
        </span>
      </td>
    </tr>
  `).join("");
}

/* ---------- User Actions ---------- */

async function handleReviewAction(jobId, action) {
  appendLog(`Review decision for job [${jobId}]: ${action.toUpperCase()}`, "warn", "human-review");

  if (isLiveApi) {
    try {
      const res = await apiFetch(`/review-queue/${jobId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ job_id: jobId, action: action, auto_submit_override: false }),
      });
      showToast(`Application for ${res.company} ${action}d successfully.`, "success");
      await loadDashboardData();
    } catch (err) {
      showToast(`Action failed: ${err.message}`, "error");
      appendLog(`Failed to record action: ${err.message}`, "error");
    }
  } else {
    // Offline simulation
    const item = currentQueue.find(q => q.job_id === jobId);
    if (item) {
      item.stage = action === "approve" ? "applied" : "rejected";
    }
    showToast(`Offline Demo: Application ${action}d (Dry Run verified).`, "success");
    renderReviewQueue(currentQueue);
    renderStats(currentMatches, currentQueue);
  }
}

async function handleResumeUpload(file) {
  appendLog(`Uploading resume file: ${file.name} (${(file.size / 1024).toFixed(1)} KB)…`, "info", "upload");
  showToast("Parsing resume and analyzing skills…", "info");

  if (isLiveApi) {
    const formData = new FormData();
    formData.append("file", file);
    try {
      const profile = await apiFetch("/resume/upload", {
        method: "POST",
        body: formData,
      });
      renderProfile(profile);
      showToast(`Parsed profile for ${profile.full_name} (${profile.skills.length} skills found)`, "success");
      appendLog(`Parsed profile for ${profile.full_name}: ${profile.skills.join(", ")}`, "success", "parser");
      await loadDashboardData();
    } catch (err) {
      showToast(`Resume parse failed: ${err.message}`, "error");
      appendLog(`Resume parse error: ${err.message}`, "error", "parser");
    }
  } else {
    showToast("Backend offline: Cannot parse live files in offline demo mode.", "error");
    appendLog("Upload rejected: Start backend server to enable live resume parsing.", "error");
  }
}

async function toggleAgent() {
  const btn = document.getElementById("btnToggleAgent");
  const dot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");

  if (isLiveApi) {
    try {
      const res = await apiFetch("/agent/toggle", { method: "POST" });
      const active = res.agent_active;
      dot.classList.toggle("active", active);
      statusText.textContent = active ? "Agent active" : "Agent idle";
      btn.textContent = active ? "Pause Agent" : "Start Agent";
      appendLog(`Agent state updated: ${active ? "ACTIVE" : "IDLE"}`, active ? "success" : "info");
    } catch (err) {
      showToast("Failed to toggle agent", "error");
    }
  } else {
    const isActive = dot.classList.toggle("active");
    statusText.textContent = isActive ? "Agent active (demo)" : "Agent idle";
    btn.textContent = isActive ? "Pause Agent" : "Start Agent";
    appendLog(`Demo agent status: ${isActive ? "ACTIVE" : "IDLE"}`);
  }
}

/* ---------- Initialization ---------- */

async function loadDashboardData() {
  try {
    // 1. Instant handshake: retrieve active candidate profile
    const profile = await apiFetch("/resume/current");
    updateConnectionBadge(true);
    renderProfile(profile);

    // 2. Retrieve review queue and summary stats
    const [queue, summary] = await Promise.all([
      apiFetch("/review-queue"),
      apiFetch("/dashboard/summary").catch(() => null),
    ]);
    renderReviewQueue(queue);
    renderStats(currentMatches, queue, summary);

    // 3. Retrieve matched jobs from scrapers (with polite board rate-limits)
    const matches = await apiFetch("/jobs/match");
    renderTable(matches);
    renderStats(matches, queue, summary);
    appendLog(`Live API synchronized. ${matches.length} matched postings, ${queue.filter(q => q.stage === "needs_review").length} pending review.`, "success", "sync");
  } catch (err) {
    updateConnectionBadge(false);
    renderProfile(SAMPLE_PROFILE);
    renderReviewQueue(SAMPLE_QUEUE);
    renderTable(SAMPLE_MATCHES);
    renderStats(SAMPLE_MATCHES, SAMPLE_QUEUE);
    appendLog(`Backend unreachable (${err.message}). Loaded fallback sample data.`, "warn", "sync");
  }
}

function initEventHandlers() {
  document.getElementById("btnToggleAgent").addEventListener("click", toggleAgent);
  document.getElementById("btnRetryConnection").addEventListener("click", loadDashboardData);

  document.getElementById("btnRunPipeline").addEventListener("click", () => {
    appendLog("Pipeline cycle triggered — evaluating postings against profile…", "info", "pipeline");
    showToast("Running pipeline match & queue cycle…", "info");
    loadDashboardData();
  });

  document.getElementById("btnClearLog").addEventListener("click", () => {
    document.getElementById("agentLog").innerHTML = "";
    appendLog("Log cleared.");
  });

  const uploadBtn = document.getElementById("btnUploadResume");
  const fileInput = document.getElementById("resumeFileInput");
  uploadBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleResumeUpload(e.target.files[0]);
    }
  });

  const searchInput = document.getElementById("jobSearchInput");
  searchInput.addEventListener("input", (e) => {
    const query = e.target.value.toLowerCase();
    const filtered = currentMatches.filter(m =>
      m.job.title.toLowerCase().includes(query) ||
      m.job.company.toLowerCase().includes(query) ||
      (m.job.description || "").toLowerCase().includes(query)
    );
    renderTable(filtered);
  });
}

async function init() {
  initEventHandlers();
  appendLog("AutoApply AI dashboard initializing…", "info", "boot");
  await loadDashboardData();
}

document.addEventListener("DOMContentLoaded", init);
