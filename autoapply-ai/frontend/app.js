/**
 * AutoApply AI — Autonomous Job Application Agent Dashboard
 * =========================================================
 * Production multi-user client supporting JWT authentication,
 * tenant data isolation, interactive profile management, multi-source
 * scraping filters, human review queue, and offline demo fallback.
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
let currentSkills = [];

// Fallback sample data for offline standalone mode
const SAMPLE_PROFILE = {
  full_name: "Alex Rivera",
  email: "alex.rivera@example.com",
  phone: "+1 (555) 789-0123",
  location: "San Francisco, CA",
  desired_role: "Senior Backend Engineer",
  desired_location: "Remote",
  remote_preference: "remote",
  skills: ["python", "fastapi", "sql", "docker", "kubernetes", "git", "rest api", "postgresql"],
  years_experience: 4.5,
  bio: "Senior backend developer experienced with distributed Python microservices, Playwright automation, and high-throughput SQL pipelines.",
  resumes: [
    {
      id: "res-sample-01",
      filename: "Alex_Rivera_Backend_2026.pdf",
      uploaded_at: new Date().toISOString(),
      is_active: true
    }
  ]
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
      source: "remoteok",
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

/* =============================================================
   Auth & Token Management
   ============================================================= */

function getAuthToken() {
  return localStorage.getItem("autoapply_access_token") || "";
}

function setAuthToken(token, user = null) {
  if (token) {
    localStorage.setItem("autoapply_access_token", token);
  }
  if (user) {
    localStorage.setItem("autoapply_user", JSON.stringify(user));
  }
}

function clearAuth() {
  localStorage.removeItem("autoapply_access_token");
  localStorage.removeItem("autoapply_user");
}

function getStoredUser() {
  try {
    const raw = localStorage.getItem("autoapply_user");
    return raw ? JSON.parse(raw) : null;
  } catch (e) {
    return null;
  }
}

function handleAuthLogout() {
  clearAuth();
  showToast("Logged out successfully.", "info");
  setTimeout(() => {
    window.location.href = "login.html?tab=login";
  }, 400);
}

/* =============================================================
   Network Helper with Auth & Auto-Redirect on 401
   ============================================================= */

async function authFetch(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = { ...(options.headers || {}) };

  if (token && !headers["Authorization"]) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 35000);

  try {
    const res = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers,
      credentials: "omit",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.status === 401) {
      // Token invalid or expired
      const path = window.location.pathname;
      if (path.includes("dashboard.html") || path.includes("profile.html")) {
        clearAuth();
        window.location.href = "login.html?tab=login&expired=true";
        throw new Error("Session expired. Please log in again.");
      }
    }

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `HTTP ${res.status}: ${res.statusText}`);
    }

    // Check content type before parsing JSON
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return await res.json();
    }
    return res;
  } catch (err) {
    clearTimeout(timeoutId);
    console.error(`[AutoApply API Error] ${endpoint}:`, err);
    throw err;
  }
}

/* =============================================================
   Notifications & Terminal Logging
   ============================================================= */

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

/* =============================================================
   Common Header & Navigation Setup
   ============================================================= */

function setupUserNav() {
  const user = getStoredUser();
  const navBadge = document.getElementById("navUserBadge");
  const btnLogout = document.getElementById("btnLogout");

  if (navBadge) {
    if (user && user.email) {
      navBadge.textContent = user.full_name ? `${user.full_name} (${user.email})` : user.email;
    } else {
      navBadge.textContent = "Account";
    }
  }

  if (btnLogout) {
    btnLogout.addEventListener("click", handleAuthLogout);
  }
}

/* =============================================================
   1. AUTH PAGE LOGIC (login.html)
   ============================================================= */

function initAuthPage() {
  const tabLogin = document.getElementById("tabLogin");
  const tabSignup = document.getElementById("tabSignup");
  const loginForm = document.getElementById("loginForm");
  const signupForm = document.getElementById("signupForm");
  const authTitle = document.getElementById("authTitle");
  const authSubtitle = document.getElementById("authSubtitle");
  const authAlert = document.getElementById("authAlert");

  // Read URL query params (?tab=signup, ?expired=true)
  const params = new URLSearchParams(window.location.search);
  if (params.get("expired") === "true") {
    authAlert.className = "auth-alert alert-error";
    authAlert.textContent = "Your session has expired. Please sign in again.";
    authAlert.style.display = "block";
  }

  function switchTab(mode) {
    authAlert.style.display = "none";
    if (mode === "signup") {
      tabSignup.classList.add("is-active");
      tabLogin.classList.remove("is-active");
      loginForm.style.display = "none";
      signupForm.style.display = "block";
      authTitle.textContent = "Create Account";
      authSubtitle.textContent = "Join AutoApply AI to deploy autonomous job agents";
    } else {
      tabLogin.classList.add("is-active");
      tabSignup.classList.remove("is-active");
      signupForm.style.display = "none";
      loginForm.style.display = "block";
      authTitle.textContent = "Welcome Back";
      authSubtitle.textContent = "Sign in to your AutoApply AI agent dashboard";
    }
  }

  if (params.get("tab") === "signup") {
    switchTab("signup");
  }

  tabLogin.addEventListener("click", () => switchTab("login"));
  tabSignup.addEventListener("click", () => switchTab("signup"));

  // Login submission
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    authAlert.style.display = "none";
    const btn = document.getElementById("btnLoginSubmit");
    const txt = document.getElementById("loginBtnText");
    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value;

    btn.disabled = true;
    txt.textContent = "Signing In...";

    try {
      const res = await authFetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      setAuthToken(res.access_token, res.user);
      authAlert.className = "auth-alert alert-success";
      authAlert.textContent = "Login successful! Redirecting to dashboard...";
      authAlert.style.display = "block";
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 500);
    } catch (err) {
      authAlert.className = "auth-alert alert-error";
      authAlert.textContent = err.message || "Invalid email or password.";
      authAlert.style.display = "block";
    } finally {
      btn.disabled = false;
      txt.textContent = "Sign In";
    }
  });

  // Signup submission
  signupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    authAlert.style.display = "none";
    const btn = document.getElementById("btnSignupSubmit");
    const txt = document.getElementById("signupBtnText");
    const full_name = document.getElementById("signupName").value.trim();
    const email = document.getElementById("signupEmail").value.trim();
    const password = document.getElementById("signupPassword").value;

    btn.disabled = true;
    txt.textContent = "Creating Account...";

    try {
      const res = await authFetch("/auth/signup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ full_name, email, password }),
      });
      setAuthToken(res.access_token, res.user);
      authAlert.className = "auth-alert alert-success";
      authAlert.textContent = "Account created! Redirecting to your dashboard...";
      authAlert.style.display = "block";
      setTimeout(() => {
        window.location.href = "dashboard.html";
      }, 500);
    } catch (err) {
      authAlert.className = "auth-alert alert-error";
      authAlert.textContent = err.message || "Could not create account.";
      authAlert.style.display = "block";
    } finally {
      btn.disabled = false;
      txt.textContent = "Create Account";
    }
  });

  // Forgot Password Toggle & Execution
  const linkForgot = document.getElementById("linkForgotPassword");
  const forgotBox = document.getElementById("forgotPasswordBox");
  if (linkForgot && forgotBox) {
    linkForgot.addEventListener("click", () => {
      forgotBox.style.display = forgotBox.style.display === "none" ? "block" : "none";
    });

    const btnSendForgotToken = document.getElementById("btnSendForgotToken");
    const forgotStep1 = document.getElementById("forgotStep1");
    const forgotStep2 = document.getElementById("forgotStep2");
    const btnConfirmReset = document.getElementById("btnConfirmReset");

    btnSendForgotToken.addEventListener("click", async () => {
      const email = document.getElementById("forgotEmail").value.trim();
      if (!email) {
        showToast("Please enter your account email.", "error");
        return;
      }
      try {
        const res = await authFetch("/auth/forgot-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email }),
        });
        showToast(res.message || "Reset token generated. Check console/logs in dev.", "info");
        forgotStep1.style.display = "none";
        forgotStep2.style.display = "block";
      } catch (err) {
        showToast(`Request failed: ${err.message}`, "error");
      }
    });

    btnConfirmReset.addEventListener("click", async () => {
      const token = document.getElementById("resetToken").value.trim();
      const new_password = document.getElementById("resetNewPassword").value;
      if (!token || !new_password) {
        showToast("Please enter both the reset token and your new password.", "error");
        return;
      }
      try {
        const res = await authFetch("/auth/reset-password", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token, new_password }),
        });
        showToast(res.message || "Password reset successfully. You can now log in.", "success");
        forgotBox.style.display = "none";
        switchTab("login");
      } catch (err) {
        showToast(`Reset failed: ${err.message}`, "error");
      }
    });
  }
}

/* =============================================================
   2. DASHBOARD PAGE LOGIC (dashboard.html)
   ============================================================= */

function updateConnectionBadge(connected) {
  isLiveApi = connected;
  const badge = document.getElementById("connectionBadge");
  const banner = document.getElementById("connectionBanner");
  const bannerMsg = document.getElementById("bannerMessage");

  if (!badge) return;

  if (connected) {
    badge.className = "badge-tag connected";
    badge.textContent = "Live API Connected";
    if (banner) banner.style.display = "none";
  } else {
    badge.className = "badge-tag standalone";
    badge.textContent = "Offline Demo Mode";
    if (banner) {
      banner.style.display = "flex";
      bannerMsg.textContent = "Backend offline (http://localhost:8000). Running in standalone demo mode with cached data.";
    }
  }
}

function renderProfileStrip(profile) {
  currentProfile = profile;
  const nameEl = document.getElementById("profileName");
  const expEl = document.getElementById("profileExp");
  const langEl = document.getElementById("profileLang");
  const contactEl = document.getElementById("profileContact");
  const avatarEl = document.getElementById("profileAvatar");
  const skillsContainer = document.getElementById("profileSkills");
  const remotePrefEl = document.getElementById("profileRemotePref");

  if (!nameEl) return;

  nameEl.textContent = profile.full_name || "Anonymous Candidate";
  expEl.textContent = profile.years_experience ? `${profile.years_experience} yrs exp` : "Entry level";
  langEl.textContent = (profile.language || "EN").toUpperCase();
  contactEl.textContent = `${profile.email || "No contact email"} • ${profile.phone || "No phone"} • ${profile.location || "Remote"}`;

  if (remotePrefEl && profile.remote_preference) {
    remotePrefEl.style.display = "inline-block";
    remotePrefEl.textContent = profile.remote_preference.toUpperCase();
  }

  const initials = (profile.full_name || "AA").split(" ").map(p => p[0]).slice(0, 2).join("").toUpperCase();
  avatarEl.textContent = initials;

  if (skillsContainer) {
    skillsContainer.innerHTML = (profile.skills || []).map(skill => `<span class="skill-chip">${skill}</span>`).join("");
  }
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

  const statMatched = document.getElementById("statMatched");
  if (statMatched) statMatched.textContent = totalScored;
  const statRecommended = document.getElementById("statRecommended");
  if (statRecommended) statRecommended.textContent = pendingReview;
  const statApplied = document.getElementById("statApplied");
  if (statApplied) statApplied.textContent = appliedCount;
  const statAvgScore = document.getElementById("statAvgScore");
  if (statAvgScore) statAvgScore.textContent = avgScore.toFixed(2);

  const cntParsed = document.getElementById("count-parsed");
  if (cntParsed) cntParsed.textContent = 1;
  const cntMatched = document.getElementById("count-matched");
  if (cntMatched) cntMatched.textContent = totalScored;
  const cntReview = document.getElementById("count-review");
  if (cntReview) cntReview.textContent = pendingReview;
  const cntApplied = document.getElementById("count-applied");
  if (cntApplied) cntApplied.textContent = appliedCount;
  const cntSubmitted = document.getElementById("count-submitted");
  if (cntSubmitted) cntSubmitted.textContent = summary ? (summary.total_submitted || 0) : 0;

  // Active track node
  const activeStage = pendingReview > 0 ? "review" : (appliedCount > 0 ? "applied" : "matched");
  document.querySelectorAll(".pipeline-stage").forEach(el => {
    el.classList.toggle("is-active", el.dataset.stage === activeStage);
  });
}

function renderSourcesStatus(sourcesStatus) {
  const container = document.getElementById("sourcesStatusContainer");
  if (!container || !sourcesStatus) return;

  const html = Object.entries(sourcesStatus).map(([source, status]) => {
    const isOk = status === "ok";
    const badgeClass = isOk ? "badge-tag connected" : "badge-tag standalone";
    const icon = isOk ? "●" : "⚠";
    return `<span class="${badgeClass}" title="Live adapter status for ${source}">
      <span style="font-size: 10px; margin-right: 4px;">${icon}</span>
      <strong>${source}</strong>: ${status}
    </span>`;
  }).join("");

  container.innerHTML = html;
}

function renderReviewQueue(queue) {
  currentQueue = queue;
  const container = document.getElementById("reviewQueueList");
  const countLabel = document.getElementById("queuePendingCount");
  if (!container) return;

  const pending = queue.filter(q => q.stage === "needs_review");
  if (countLabel) countLabel.textContent = `${pending.length} pending review`;

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
        <div class="action-buttons" style="display: flex; gap: 8px; flex-wrap: wrap;">
          <button class="btn btn-sm btn-outline" onclick="openScreenshotModal('${item.job_id}', '${encodeURIComponent(item.title)}')">
            📷 Form Snapshot
          </button>
          <button class="btn btn-sm btn-secondary" onclick="openCoverLetterModal('${item.job_id}', '${encodeURIComponent(item.title)}', '${encodeURIComponent(item.company)}')">
            ✍️ Cover Letter
          </button>
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
  if (!body) return;

  if (!matches.length) {
    body.innerHTML = `<tr><td colspan="6" class="empty-row">No matching job postings found.</td></tr>`;
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
      <td>
        <button class="btn btn-xs btn-outline" onclick="openCoverLetterModal('${m.job.id}', '${encodeURIComponent(m.job.title)}', '${encodeURIComponent(m.job.company)}')">
          Cover Note
        </button>
      </td>
    </tr>
  `).join("");
}

/* ---------- User Actions on Dashboard ---------- */

async function handleReviewAction(jobId, action) {
  appendLog(`Review decision for job [${jobId}]: ${action.toUpperCase()}`, "warn", "human-review");

  if (isLiveApi) {
    try {
      const res = await authFetch(`/review-queue/${jobId}/action`, {
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
      const profile = await authFetch("/profile/resume?auto_populate_suggestions=true", {
        method: "POST",
        body: formData,
      });
      renderProfileStrip(profile);
      showToast(`Parsed profile for ${profile.full_name} (${(profile.skills || []).length} skills found)`, "success");
      appendLog(`Parsed profile for ${profile.full_name}: ${(profile.skills || []).join(", ")}`, "success", "parser");
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
      const res = await authFetch("/agent/toggle", { method: "POST" });
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

/* ---------- Modals: Screenshot & Cover Letter ---------- */

async function openScreenshotModal(jobId, titleEncoded) {
  const title = decodeURIComponent(titleEncoded);
  const modal = document.getElementById("screenshotModal");
  const titleEl = document.getElementById("screenshotModalTitle");
  const loadingEl = document.getElementById("screenshotLoading");
  const imgEl = document.getElementById("screenshotImg");

  titleEl.textContent = `Form Snapshot: ${title}`;
  loadingEl.style.display = "block";
  imgEl.style.display = "none";
  modal.classList.add("is-open");

  if (!isLiveApi) {
    loadingEl.style.display = "none";
    imgEl.src = "page_inspect.png"; // Fallback static screenshot
    imgEl.style.display = "inline-block";
    return;
  }

  try {
    const token = getAuthToken();
    const res = await fetch(`${API_BASE}/screenshots/${jobId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    if (!res.ok) throw new Error("Snapshot not found for this job run.");
    const blob = await res.blob();
    imgEl.src = URL.createObjectURL(blob);
    loadingEl.style.display = "none";
    imgEl.style.display = "inline-block";
  } catch (err) {
    loadingEl.innerHTML = `<span style="color: var(--accent-amber);">⚠ ${err.message}</span>`;
  }
}

async function openCoverLetterModal(jobId, titleEncoded, companyEncoded) {
  const title = decodeURIComponent(titleEncoded);
  const company = decodeURIComponent(companyEncoded);
  const modal = document.getElementById("coverLetterModal");
  const titleEl = document.getElementById("coverLetterModalTitle");
  const loadingEl = document.getElementById("coverLetterLoading");
  const textEl = document.getElementById("coverLetterText");

  titleEl.textContent = `Tailored Application Note: ${company} — ${title}`;
  loadingEl.style.display = "block";
  textEl.value = "";
  modal.classList.add("is-open");

  if (!isLiveApi) {
    loadingEl.style.display = "none";
    textEl.value = `Dear Hiring Team at ${company},\n\nI am writing to express my strong interest in the ${title} position. With over 4.5 years of experience building high-throughput Python backends and distributed architectures, I am eager to contribute.\n\nBest regards,\nAlex Rivera`;
    return;
  }

  try {
    const res = await authFetch("/cover-letter/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        job_id: jobId,
        job_title: title,
        company: company,
        job_description: ""
      }),
    });
    loadingEl.style.display = "none";
    textEl.value = res.cover_letter;
  } catch (err) {
    loadingEl.style.display = "none";
    textEl.value = `Error generating cover letter: ${err.message}`;
  }
}

function initModalHandlers() {
  const closeScreenshot = () => document.getElementById("screenshotModal")?.classList.remove("is-open");
  const closeCover = () => document.getElementById("coverLetterModal")?.classList.remove("is-open");

  document.getElementById("btnCloseScreenshotModal")?.addEventListener("click", closeScreenshot);
  document.getElementById("btnCloseScreenshotModal2")?.addEventListener("click", closeScreenshot);
  document.getElementById("btnCloseCoverModal")?.addEventListener("click", closeCover);
  document.getElementById("btnCloseCoverModal2")?.addEventListener("click", closeCover);

  document.getElementById("btnCopyCoverLetter")?.addEventListener("click", () => {
    const text = document.getElementById("coverLetterText")?.value;
    if (text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast("Cover letter copied to clipboard!", "success");
      });
    }
  });
}

/* ---------- Load Dashboard Data ---------- */

async function loadDashboardData(searchParams = {}) {
  try {
    // 1. Profile handshake
    const profile = await authFetch("/profile");
    updateConnectionBadge(true);
    renderProfileStrip(profile);

    // 2. Queue and summary
    const [queue, summary] = await Promise.all([
      authFetch("/review-queue"),
      authFetch("/dashboard/summary").catch(() => null),
    ]);
    renderReviewQueue(queue);
    renderStats(currentMatches, queue, summary);

    // 3. Matched jobs with multi-source filter query
    let matchUrl = "/jobs/match";
    const queryParts = [];
    if (searchParams.query) queryParts.push(`query=${encodeURIComponent(searchParams.query)}`);
    if (searchParams.location) queryParts.push(`location=${encodeURIComponent(searchParams.location)}`);
    if (searchParams.sources && searchParams.sources.length) {
      queryParts.push(`sources=${encodeURIComponent(searchParams.sources.join(","))}`);
    }
    if (queryParts.length) matchUrl += `?${queryParts.join("&")}`;

    const matchResponse = await authFetch(matchUrl);
    // Response can be JobMatchResponse { matches: [...], sources_status: {...} } or list of matches
    const matchesList = matchResponse.matches || matchResponse;
    const sourcesStatus = matchResponse.sources_status || null;

    renderTable(matchesList);
    renderStats(matchesList, queue, summary);
    if (sourcesStatus) renderSourcesStatus(sourcesStatus);

    appendLog(`Live API synchronized. ${matchesList.length} matched postings, ${queue.filter(q => q.stage === "needs_review").length} pending review.`, "success", "sync");
  } catch (err) {
    updateConnectionBadge(false);
    renderProfileStrip(SAMPLE_PROFILE);
    renderReviewQueue(SAMPLE_QUEUE);
    renderTable(SAMPLE_MATCHES);
    renderStats(SAMPLE_MATCHES, SAMPLE_QUEUE);
    appendLog(`Backend unreachable (${err.message}). Loaded fallback sample data.`, "warn", "sync");
  }
}

function initDashboardPage() {
  setupUserNav();
  initModalHandlers();

  document.getElementById("btnToggleAgent")?.addEventListener("click", toggleAgent);
  document.getElementById("btnRetryConnection")?.addEventListener("click", () => loadDashboardData());

  document.getElementById("btnRunPipeline")?.addEventListener("click", () => {
    appendLog("Pipeline cycle triggered — evaluating postings against profile…", "info", "pipeline");
    showToast("Running match & queue cycle…", "info");
    loadDashboardData();
  });

  document.getElementById("btnClearLog")?.addEventListener("click", () => {
    const el = document.getElementById("agentLog");
    if (el) el.innerHTML = "";
    appendLog("Log cleared.");
  });

  const uploadBtn = document.getElementById("btnUploadResume");
  const fileInput = document.getElementById("resumeFileInput");
  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click());
    fileInput.addEventListener("change", (e) => {
      if (e.target.files.length > 0) {
        handleResumeUpload(e.target.files[0]);
      }
    });
  }

  // Multi-source Search Form
  const searchForm = document.getElementById("jobSearchForm");
  if (searchForm) {
    searchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const query = document.getElementById("searchKeywords").value.trim();
      const location = document.getElementById("searchLocation").value.trim();
      const sources = Array.from(document.querySelectorAll("input[name='sources']:checked")).map(cb => cb.value);

      appendLog(`Searching jobs: keywords="${query}", location="${location}", sources=${sources.join(",")}`, "info", "search");
      showToast("Searching live job sources...", "info");
      loadDashboardData({ query, location, sources });
    });
  }

  // Filter existing table
  const searchInput = document.getElementById("jobSearchInput");
  if (searchInput) {
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

  appendLog("AutoApply AI dashboard initializing…", "info", "boot");
  loadDashboardData();
}

/* =============================================================
   3. PROFILE PAGE LOGIC (profile.html)
   ============================================================= */

function renderSkillsTags() {
  const container = document.getElementById("skillsTagsContainer");
  if (!container) return;

  if (!currentSkills.length) {
    container.innerHTML = `<span style="color: var(--text-muted); font-size: 13px;">No skills added yet. Type below to add.</span>`;
    return;
  }

  container.innerHTML = currentSkills.map(skill => `
    <span class="skill-editable-tag">
      ${skill}
      <span class="skill-tag-remove" onclick="removeSkill('${skill}')">&times;</span>
    </span>
  `).join("");
}

function addSkill(skillName) {
  const clean = skillName.trim().toLowerCase();
  if (clean && !currentSkills.includes(clean)) {
    currentSkills.push(clean);
    renderSkillsTags();
  }
}

function removeSkill(skillName) {
  currentSkills = currentSkills.filter(s => s !== skillName);
  renderSkillsTags();
}

function renderResumesTable(resumes) {
  const body = document.getElementById("resumesListBody");
  if (!body) return;

  if (!resumes || !resumes.length) {
    body.innerHTML = `<tr><td colspan="4" class="empty-row" style="text-align: center; padding: 20px; color: var(--text-muted);">No resumes uploaded yet.</td></tr>`;
    return;
  }

  body.innerHTML = resumes.map(r => `
    <tr>
      <td><strong>${r.filename}</strong></td>
      <td>${new Date(r.uploaded_at).toLocaleDateString()} ${new Date(r.uploaded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</td>
      <td>
        <span class="badge-tag ${r.is_active ? "connected" : ""}">
          ${r.is_active ? "Active" : "Archived"}
        </span>
      </td>
      <td>
        <button class="btn btn-xs btn-danger" onclick="deleteResumeVersion('${r.id}')">
          Delete
        </button>
      </td>
    </tr>
  `).join("");
}

async function deleteResumeVersion(resumeId) {
  if (!confirm("Are you sure you want to delete this resume version?")) return;
  try {
    await authFetch(`/profile/resume/${resumeId}`, { method: "DELETE" });
    showToast("Resume version deleted.", "success");
    await loadFullProfile();
  } catch (err) {
    showToast(`Delete failed: ${err.message}`, "error");
  }
}

async function loadFullProfile() {
  try {
    const profile = await authFetch("/profile");
    currentProfile = profile;
    currentSkills = [...(profile.skills || [])];

    document.getElementById("profFullName").value = profile.full_name || "";
    document.getElementById("profEmail").value = profile.email || "";
    document.getElementById("profPhone").value = profile.phone || "";
    document.getElementById("profLocation").value = profile.location || "";
    document.getElementById("profLinkedIn").value = profile.linkedin_url || "";
    document.getElementById("profGitHub").value = profile.github_url || "";
    document.getElementById("profPortfolio").value = profile.portfolio_url || "";
    document.getElementById("profDesiredRole").value = profile.desired_role || "";
    document.getElementById("profDesiredLocation").value = profile.desired_location || "";
    document.getElementById("profRemotePref").value = profile.remote_preference || "any";
    document.getElementById("profYearsExp").value = profile.years_experience !== null ? profile.years_experience : "";
    document.getElementById("profBio").value = profile.bio || "";

    const updatedEl = document.getElementById("profileLastUpdated");
    if (updatedEl) {
      updatedEl.textContent = profile.updated_at ? new Date(profile.updated_at).toLocaleString() : "Recently";
    }

    renderSkillsTags();
    renderResumesTable(profile.resumes || []);
  } catch (err) {
    showToast(`Failed to load profile: ${err.message}`, "error");
    // Fallback to sample
    currentProfile = SAMPLE_PROFILE;
    currentSkills = [...SAMPLE_PROFILE.skills];
    renderSkillsTags();
    renderResumesTable(SAMPLE_PROFILE.resumes);
  }
}

function initProfilePage() {
  setupUserNav();

  // Skills input handlers
  const inputSkill = document.getElementById("inputNewSkill");
  const btnAddSkill = document.getElementById("btnAddSkill");

  const submitSkill = () => {
    if (inputSkill && inputSkill.value) {
      addSkill(inputSkill.value);
      inputSkill.value = "";
    }
  };

  btnAddSkill?.addEventListener("click", submitSkill);
  inputSkill?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      submitSkill();
    }
  });

  // Profile Form Save
  const form = document.getElementById("profileEditForm");
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("btnSaveProfile");
    btn.disabled = true;
    btn.textContent = "Saving...";

    const yearsRaw = document.getElementById("profYearsExp").value;
    const payload = {
      full_name: document.getElementById("profFullName").value.trim() || null,
      email: document.getElementById("profEmail").value.trim() || null,
      phone: document.getElementById("profPhone").value.trim() || null,
      location: document.getElementById("profLocation").value.trim() || null,
      linkedin_url: document.getElementById("profLinkedIn").value.trim() || null,
      github_url: document.getElementById("profGitHub").value.trim() || null,
      portfolio_url: document.getElementById("profPortfolio").value.trim() || null,
      desired_role: document.getElementById("profDesiredRole").value.trim() || null,
      desired_location: document.getElementById("profDesiredLocation").value.trim() || null,
      remote_preference: document.getElementById("profRemotePref").value || "any",
      years_experience: yearsRaw ? parseFloat(yearsRaw) : null,
      skills: currentSkills,
      bio: document.getElementById("profBio").value.trim() || null,
    };

    try {
      const res = await authFetch("/profile", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      showToast("Profile changes saved successfully!", "success");
      const updatedEl = document.getElementById("profileLastUpdated");
      if (updatedEl) updatedEl.textContent = new Date().toLocaleString();
    } catch (err) {
      showToast(`Save failed: ${err.message}`, "error");
    } finally {
      btn.disabled = false;
      btn.textContent = "💾 Save Profile Changes";
    }
  });

  document.getElementById("btnResetProfile")?.addEventListener("click", () => {
    loadFullProfile();
    showToast("Form reset to saved profile values.", "info");
  });

  // Resume Upload Handlers on Profile Page
  const btnSelectFile = document.getElementById("btnSelectResumeFile");
  const fileInput = document.getElementById("profileResumeFileInput");
  const fileNameDisplay = document.getElementById("selectedResumeFileName");
  const btnUploadFile = document.getElementById("btnUploadResumeFile");

  btnSelectFile?.addEventListener("click", () => fileInput?.click());
  fileInput?.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      const file = e.target.files[0];
      fileNameDisplay.textContent = `${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
      btnUploadFile.style.display = "inline-block";
    }
  });

  btnUploadFile?.addEventListener("click", async () => {
    if (!fileInput.files.length) return;
    const file = fileInput.files[0];
    const populate = document.getElementById("checkPopulateSuggestions").checked;

    btnUploadFile.disabled = true;
    btnUploadFile.textContent = "Parsing Resume...";
    showToast("Uploading and parsing resume with skill extraction...", "info");

    const formData = new FormData();
    formData.append("file", file);

    try {
      await authFetch(`/profile/resume?auto_populate_suggestions=${populate}`, {
        method: "POST",
        body: formData,
      });
      showToast("Resume uploaded, versioned, and parsed successfully!", "success");
      fileInput.value = "";
      fileNameDisplay.textContent = "";
      btnUploadFile.style.display = "none";
      await loadFullProfile();
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, "error");
    } finally {
      btnUploadFile.disabled = false;
      btnUploadFile.textContent = "⬆ Upload & Parse Resume";
    }
  });

  loadFullProfile();
}

/* =============================================================
   4. LANDING PAGE LOGIC (index.html)
   ============================================================= */

function initLandingPage() {
  const token = getAuthToken();
  if (token) {
    // If logged in, update topbar and hero buttons to "Go to Dashboard"
    const authNavButtons = document.getElementById("authNavButtons");
    if (authNavButtons) {
      authNavButtons.innerHTML = `<a href="dashboard.html" class="btn btn-primary btn-sm">Go to Dashboard →</a>`;
    }
    const heroBtn = document.getElementById("heroGetStartedBtn");
    if (heroBtn) {
      heroBtn.textContent = "Go to Dashboard →";
      heroBtn.href = "dashboard.html";
    }
  }
}

/* =============================================================
   App Entrypoint & Router
   ============================================================= */

function init() {
  if (document.getElementById("loginForm")) {
    initAuthPage();
  } else if (document.getElementById("reviewQueueList")) {
    // Protected route
    const token = getAuthToken();
    if (!token) {
      window.location.href = "login.html?tab=login";
      return;
    }
    initDashboardPage();
  } else if (document.getElementById("profileEditForm")) {
    // Protected route
    const token = getAuthToken();
    if (!token) {
      window.location.href = "login.html?tab=login";
      return;
    }
    initProfilePage();
  } else if (document.getElementById("publicNav")) {
    initLandingPage();
  }
}

document.addEventListener("DOMContentLoaded", init);
