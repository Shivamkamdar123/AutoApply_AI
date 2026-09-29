// AutoApply AI Copilot - Content Script
// Injected into LinkedIn, Indeed, and Naukri job posting pages.
// ZERO credentials stored, ZERO automated logins, explicit per-job click required.

(function () {
  if (window.__AUTOAPPLY_COPILOT_INITIALIZED__) return;
  window.__AUTOAPPLY_COPILOT_INITIALIZED__ = true;

  let backendUrl = "http://127.0.0.1:8000";
  let authToken = "";
  let currentJobData = null;
  let proposedDecisions = [];

  // Load storage config
  if (chrome.storage && chrome.storage.local) {
    chrome.storage.local.get(["apiUrl", "authToken"], (res) => {
      if (res.apiUrl) backendUrl = res.apiUrl.replace(/\/$/, "");
      if (res.authToken) authToken = res.authToken;
      initCopilot();
    });
  } else {
    initCopilot();
  }

  function initCopilot() {
    // Check if on a job page after a short DOM settle delay
    setTimeout(() => {
      detectAndInject();
    }, 1200);

    // Watch for single-page app navigation (LinkedIn/Indeed dynamic navigation)
    let lastUrl = location.href;
    new MutationObserver(() => {
      if (location.href !== lastUrl) {
        lastUrl = location.href;
        setTimeout(detectAndInject, 1500);
      }
    }).observe(document, { subtree: true, childList: true });
  }

  function extractJobDetails() {
    const host = window.location.hostname;
    let title = "";
    let company = "";
    let location = "";
    let description = "";

    if (host.includes("linkedin.com")) {
      const titleEl = document.querySelector(".job-details-jobs-unified-top-card__job-title, .jobs-unified-top-card__job-title, h1.t-24, h1");
      const compEl = document.querySelector(".job-details-jobs-unified-top-card__company-name, .jobs-unified-top-card__company-name, a[href*='/company/']");
      const locEl = document.querySelector(".job-details-jobs-unified-top-card__primary-description-container, .jobs-unified-top-card__bullet");
      const descEl = document.querySelector("#job-details, .jobs-description__content, .jobs-box__html-content");

      title = titleEl ? titleEl.innerText.trim() : "";
      company = compEl ? compEl.innerText.trim() : "";
      location = locEl ? locEl.innerText.trim() : "Remote";
      description = descEl ? descEl.innerText.trim() : "";
    } else if (host.includes("indeed.com")) {
      const titleEl = document.querySelector("h1[data-testid='jobsearch-JobInfoHeader-title'], h1.jobsearch-JobInfoHeader-title, h1");
      const compEl = document.querySelector("[data-testid='inlineHeader-companyName'], div[data-company-name='true']");
      const locEl = document.querySelector("[data-testid='inlineHeader-companyLocation'], div[data-testid='jobsearch-JobInfoHeader-companyLocation']");
      const descEl = document.querySelector("#jobDescriptionText, .jobsearch-JobComponent-description");

      title = titleEl ? titleEl.innerText.trim() : "";
      company = compEl ? compEl.innerText.trim() : "";
      location = locEl ? locEl.innerText.trim() : "Remote";
      description = descEl ? descEl.innerText.trim() : "";
    } else if (host.includes("naukri.com")) {
      const titleEl = document.querySelector(".styles_header__job-title__18n1m, h1.styles_header__job-title__18n1m, h1");
      const compEl = document.querySelector(".styles_header__comp-name__npLzV, a.comp-name");
      const locEl = document.querySelector(".styles_header__loc__1jFw1, .location");
      const descEl = document.querySelector(".styles_job-desc-container__txpYf, .dang-inner-html");

      title = titleEl ? titleEl.innerText.trim() : "";
      company = compEl ? compEl.innerText.trim() : "";
      location = locEl ? locEl.innerText.trim() : "Remote";
      description = descEl ? descEl.innerText.trim() : "";
    }

    if (!title && !company) return null;

    const jobId = `${host.split(".")[1] || "job"}-${Date.now().toString(36)}`;
    return {
      job_id: jobId,
      title: title || document.title,
      company: company || "Hiring Company",
      location: location || "Remote",
      description: description || title,
      url: window.location.href,
    };
  }

  function detectAndInject() {
    const job = extractJobDetails();
    if (!job) return;

    currentJobData = job;
    renderCopilotWidget(job);
    fetchAtsGap(job);
  }

  function renderCopilotWidget(job) {
    let root = document.getElementById("autoapply-copilot-root");
    if (!root) {
      root = document.createElement("div");
      root.id = "autoapply-copilot-root";
      document.body.appendChild(root);
    }

    root.innerHTML = `
      <div class="copilot-header">
        <div class="copilot-brand">
          <div class="copilot-dot"></div>
          <span class="copilot-title">AutoApply</span>
          <span class="copilot-badge">Copilot</span>
        </div>
        <div class="copilot-actions">
          <button class="copilot-icon-btn" id="copilot-min-btn" title="Minimize">_</button>
          <button class="copilot-icon-btn" id="copilot-close-btn" title="Close">x</button>
        </div>
      </div>

      <div class="copilot-body" id="copilot-body">
        <div class="copilot-job-card">
          <div class="copilot-job-title">${escapeHtml(job.title)}</div>
          <div class="copilot-job-meta">${escapeHtml(job.company)} &bull; ${escapeHtml(job.location)}</div>
        </div>

        <div class="copilot-score-banner" id="copilot-score-banner">
          <div>
            <div class="copilot-score-text">ATS Profile Match</div>
            <div style="font-size: 10px; color: #94a3b8;">Real-time resume alignment</div>
          </div>
          <div class="copilot-score-val" id="copilot-score-val">--%</div>
        </div>

        <div class="copilot-keywords" id="copilot-keywords" style="display: none;">
          <div class="copilot-kw-title">Keyword Alignment</div>
          <div class="copilot-kw-list" id="copilot-kw-list"></div>
        </div>

        <!-- Workflow Step Area -->
        <div id="copilot-workflow-area">
          <div class="copilot-step-box">
            <div class="copilot-step-title">
              <span class="copilot-step-num">1</span>
              <span>Review & Prepare Application</span>
            </div>
            <p style="font-size: 11px; color: #94a3b8; margin-bottom: 8px;">
              Scan active form inputs and map values with transparent human oversight.
            </p>
            <button class="copilot-btn copilot-btn-primary" id="copilot-prepare-btn">
              Prepare Application
            </button>
          </div>
        </div>

        <div class="copilot-status-msg" id="copilot-status">Ready to prepare</div>
      </div>
    `;

    document.getElementById("copilot-min-btn").addEventListener("click", () => {
      root.classList.toggle("minimized");
      if (root.classList.contains("minimized")) {
        root.innerHTML = `<span style="font-size: 12px; font-weight: 600; color: #34d399;">AutoApply AI</span>`;
        root.onclick = () => {
          root.onclick = null;
          root.classList.remove("minimized");
          renderCopilotWidget(currentJobData);
        };
      }
    });

    document.getElementById("copilot-close-btn").addEventListener("click", () => {
      root.remove();
    });

    document.getElementById("copilot-prepare-btn").addEventListener("click", handlePrepareClick);
  }

  async function fetchAtsGap(job) {
    if (!authToken) return;
    try {
      const res = await fetch(`${backendUrl}/api/ats/keyword-gap`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          job_id: job.job_id,
          job_title: job.title,
          job_description: job.description,
          company: job.company,
        }),
      });

      if (!res.ok) return;
      const data = await res.json();

      const scoreEl = document.getElementById("copilot-score-val");
      if (scoreEl) scoreEl.textContent = `${Math.round(data.ats_score)}%`;

      const kwContainer = document.getElementById("copilot-keywords");
      const kwList = document.getElementById("copilot-kw-list");
      if (kwContainer && kwList) {
        kwList.innerHTML = "";
        (data.matched_keywords || []).slice(0, 5).forEach((kw) => {
          const span = document.createElement("span");
          span.className = "copilot-kw-tag copilot-kw-matched";
          span.textContent = `+ ${kw}`;
          kwList.appendChild(span);
        });
        (data.missing_keywords || []).slice(0, 4).forEach((kw) => {
          const span = document.createElement("span");
          span.className = "copilot-kw-tag copilot-kw-missing";
          span.textContent = `! ${kw}`;
          kwList.appendChild(span);
        });
        kwContainer.style.display = "block";
      }
    } catch (_) {}
  }

  function detectFormFields() {
    const fields = [];
    const elements = document.querySelectorAll("input:not([type='hidden']):not([type='submit']), textarea, select");

    elements.forEach((el, idx) => {
      const tag = el.tagName.toLowerCase();
      const inputType = el.getAttribute("type") || "text";
      const name = el.getAttribute("name") || el.getAttribute("id") || `field_${idx}`;
      const placeholder = el.getAttribute("placeholder") || "";
      const ariaLabel = el.getAttribute("aria-label") || "";

      let labelText = "";
      if (el.id) {
        const lbl = document.querySelector(`label[for="${el.id}"]`);
        if (lbl) labelText = lbl.innerText.trim();
      }
      if (!labelText && el.closest("label")) {
        labelText = el.closest("label").innerText.trim();
      }

      // Generate unique selector
      let selector = "";
      if (el.id) selector = `#${el.id}`;
      else if (el.name) selector = `${tag}[name="${el.name}"]`;
      else selector = `${tag}:nth-of-type(${idx + 1})`;

      fields.push({
        selector: selector,
        name: name,
        field_type: inputType === "textarea" ? "textarea" : inputType,
        label: labelText || ariaLabel || name,
        placeholder: placeholder,
        required: !!el.required,
      });
    });

    return fields;
  }

  async function handlePrepareClick() {
    const statusEl = document.getElementById("copilot-status");
    const prepBtn = document.getElementById("copilot-prepare-btn");
    prepBtn.disabled = true;
    statusEl.textContent = "Scanning page fields & consulting agent...";

    const detected = detectFormFields();

    try {
      const headers = { "Content-Type": "application/json" };
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const res = await fetch(`${backendUrl}/api/browser/map-fields`, {
        method: "POST",
        headers: headers,
        body: JSON.stringify({
          fields: detected,
          job_title: currentJobData.title,
          company: currentJobData.company,
          job_description: currentJobData.description,
        }),
      });

      if (!res.ok) throw new Error(`Mapping failed (${res.status})`);
      proposedDecisions = await res.json();

      // Sync event to backend tracker
      await syncEvent("needs_review", "prepared", "Application fields mapped & proposed inline");

      renderReviewStep(proposedDecisions);
      statusEl.textContent = `Mapped ${proposedDecisions.length} fields. Review below.`;
    } catch (e) {
      statusEl.textContent = `Error: ${e.message}. Is backend running?`;
      prepBtn.disabled = false;
    }
  }

  function renderReviewStep(decisions) {
    const area = document.getElementById("copilot-workflow-area");
    if (!area) return;

    let fieldsHtml = "";
    decisions.forEach((d, idx) => {
      const isTextarea = d.field_type === "textarea" || (d.value_filled && d.value_filled.length > 60);
      fieldsHtml += `
        <div class="copilot-field-row">
          <label class="copilot-field-label">${escapeHtml(d.field_name)} <span style="color:#10b981;">(${Math.round(d.confidence * 100)}%)</span></label>
          ${
            isTextarea
              ? `<textarea class="copilot-input copilot-edit-field" data-idx="${idx}">${escapeHtml(d.value_filled)}</textarea>`
              : `<input type="text" class="copilot-input copilot-edit-field" data-idx="${idx}" value="${escapeHtml(d.value_filled)}">`
          }
        </div>
      `;
    });

    area.innerHTML = `
      <div class="copilot-step-box">
        <div class="copilot-step-title">
          <span class="copilot-step-num">2</span>
          <span>Review Proposed Form Values</span>
        </div>
        <div style="max-height: 220px; overflow-y: auto; margin-bottom: 10px;">
          ${fieldsHtml || "<p style='font-size:11px;color:#94a3b8;'>No standard form fields detected on active view.</p>"}
        </div>
        <button class="copilot-btn copilot-btn-accent" id="copilot-fill-btn">
          Fill Form on Page
        </button>
      </div>
    `;

    document.getElementById("copilot-fill-btn").addEventListener("click", handleFillClick);
  }

  async function handleFillClick() {
    const statusEl = document.getElementById("copilot-status");
    statusEl.textContent = "Autofilling form fields on page...";

    // Read back any edited values
    document.querySelectorAll(".copilot-edit-field").forEach((input) => {
      const idx = parseInt(input.dataset.idx, 10);
      if (proposedDecisions[idx]) {
        proposedDecisions[idx].value_filled = input.value;
      }
    });

    // Client-side DOM manipulation on user's own tab
    let filledCount = 0;
    proposedDecisions.forEach((decision) => {
      try {
        let el = document.querySelector(decision.selector);
        if (!el && decision.field_name) {
          // Fallback search by label/name
          const term = decision.field_name.toLowerCase();
          if (term.includes("first")) el = document.querySelector("input[name*='first'], input[id*='first']");
          else if (term.includes("last")) el = document.querySelector("input[name*='last'], input[id*='last']");
          else if (term.includes("email")) el = document.querySelector("input[type='email'], input[name*='email']");
          else if (term.includes("phone")) el = document.querySelector("input[type='tel'], input[name*='phone']");
        }

        if (el) {
          el.value = decision.value_filled;
          // Dispatch native input/change events so React/Vue forms accept the fill
          el.dispatchEvent(new Event("input", { bubbles: true }));
          el.dispatchEvent(new Event("change", { bubbles: true }));
          el.dispatchEvent(new Event("blur", { bubbles: true }));
          filledCount++;
        }
      } catch (_) {}
    });

    await syncEvent("needs_review", "filled", `Autofilled ${filledCount} DOM fields on page`);

    renderApplyStep(filledCount);
    statusEl.textContent = `Filled ${filledCount} fields on page. Verify and click Apply Now.`;
    statusEl.className = "copilot-status-msg success";
  }

  function renderApplyStep(filledCount) {
    const area = document.getElementById("copilot-workflow-area");
    if (!area) return;

    area.innerHTML = `
      <div class="copilot-step-box">
        <div class="copilot-step-title">
          <span class="copilot-step-num">3</span>
          <span>Final Human Approval</span>
        </div>
        <p style="font-size: 11px; color: #94a3b8; margin-bottom: 10px; line-height: 1.4;">
          Fields filled. Verify the form on page, then click below to complete the application for this role.
        </p>
        <button class="copilot-btn copilot-btn-apply" id="copilot-apply-btn">
          Apply Now (Explicit Approval)
        </button>
      </div>
    `;

    document.getElementById("copilot-apply-btn").addEventListener("click", handleApplyClick);
  }

  async function handleApplyClick() {
    const statusEl = document.getElementById("copilot-status");
    const applyBtn = document.getElementById("copilot-apply-btn");
    applyBtn.disabled = true;
    statusEl.textContent = "Finalizing application...";

    // Try to trigger page's own submit button if present
    const submitBtn = document.querySelector("button[type='submit'], input[type='submit'], button.jobs-apply-button");
    if (submitBtn) {
      try {
        submitBtn.click();
      } catch (_) {}
    }

    // Sync to backend dashboard as "applied"
    await syncEvent("applied", "apply_click", "Application finalized via AutoApply Copilot");

    const area = document.getElementById("copilot-workflow-area");
    if (area) {
      area.innerHTML = `
        <div class="copilot-step-box" style="text-align: center; border-color: rgba(16, 185, 129, 0.4); background: rgba(16, 185, 129, 0.08);">
          <div style="font-size: 20px; margin-bottom: 6px;">&#10004;</div>
          <div style="font-weight: 700; color: #34d399; margin-bottom: 4px;">Applied Successfully!</div>
          <div style="font-size: 11px; color: #94a3b8;">
            Synced to your AutoApply dashboard application tracker.
          </div>
        </div>
      `;
    }
    statusEl.textContent = "Completed & synced!";
    statusEl.className = "copilot-status-msg success";
  }

  async function syncEvent(stage, eventType, notes) {
    if (!authToken || !currentJobData) return;
    try {
      await fetch(`${backendUrl}/api/applications/extension-event`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({
          job_id: currentJobData.job_id,
          url: currentJobData.url,
          company: currentJobData.company,
          title: currentJobData.title,
          stage: stage,
          event_type: eventType,
          notes: notes,
          field_mappings: proposedDecisions,
        }),
      });
    } catch (_) {}
  }

  function escapeHtml(str) {
    if (!str) return "";
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
})();
