// AutoApply AI Copilot Popup Controller

document.addEventListener("DOMContentLoaded", async () => {
  const apiUrlInput = document.getElementById("api-url");
  const authTokenInput = document.getElementById("auth-token");
  const saveBtn = document.getElementById("save-btn");
  const openAppBtn = document.getElementById("open-app-btn");

  const connectionDot = document.getElementById("connection-dot");
  const connectionLabel = document.getElementById("connection-label");
  const userNameEl = document.getElementById("user-name");
  const resumeStatusEl = document.getElementById("resume-status");
  const skillsCountEl = document.getElementById("skills-count");

  // Load existing config
  chrome.storage.local.get(["apiUrl", "authToken"], (res) => {
    if (res.apiUrl) apiUrlInput.value = res.apiUrl;
    if (res.authToken) authTokenInput.value = res.authToken;
    verifyBackend(apiUrlInput.value || "http://127.0.0.1:8000", res.authToken || "");
  });

  saveBtn.addEventListener("click", () => {
    const apiUrl = apiUrlInput.value.trim().replace(/\/$/, "");
    const authToken = authTokenInput.value.trim();

    chrome.storage.local.set({ apiUrl, authToken }, () => {
      saveBtn.textContent = "Saved!";
      setTimeout(() => (saveBtn.textContent = "Save & Sync Connection"), 1500);
      verifyBackend(apiUrl, authToken);
    });
  });

  openAppBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: "http://127.0.0.1:3000" });
  });

  async function verifyBackend(apiUrl, token) {
    connectionDot.className = "status-dot";
    connectionLabel.textContent = "Testing connection...";

    try {
      const healthRes = await fetch(`${apiUrl}/api/health`, { method: "GET" });
      if (!healthRes.ok) throw new Error("Health check failed");

      connectionDot.className = "status-dot connected";
      connectionLabel.textContent = "Connected to AutoApply Backend";

      if (token) {
        try {
          const profRes = await fetch(`${apiUrl}/api/profile`, {
            headers: { Authorization: `Bearer ${token}` },
          });
          if (profRes.ok) {
            const prof = await profRes.json();
            userNameEl.textContent = prof.full_name || prof.email || "Active User";
            resumeStatusEl.textContent = prof.active_resume_id ? "Active Resume" : "No Resume Uploaded";
            skillsCountEl.textContent = `${(prof.skills || []).length} extracted`;
            return;
          }
        } catch (_) {}
      }

      userNameEl.textContent = "Set Token Above";
      resumeStatusEl.textContent = "Auth Required";
      skillsCountEl.textContent = "-";
    } catch (e) {
      connectionDot.className = "status-dot error";
      connectionLabel.textContent = "Cannot reach backend (start with run_backend.bat)";
      userNameEl.textContent = "Offline";
      resumeStatusEl.textContent = "-";
      skillsCountEl.textContent = "-";
    }
  }
});
