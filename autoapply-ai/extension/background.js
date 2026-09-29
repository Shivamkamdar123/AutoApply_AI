// AutoApply AI Copilot - Background Service Worker (Manifest V3)

chrome.runtime.onInstalled.addListener((details) => {
  if (details.reason === "install") {
    // Set default backend API URL on first install
    chrome.storage.local.set({
      apiUrl: "http://127.0.0.1:8000",
      authToken: "",
    });
    console.log("AutoApply AI Copilot installed. Ready to assist on LinkedIn, Indeed, and Naukri.");
  }
});

// Message listener for future cross-context extension events
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "get_status") {
    chrome.storage.local.get(["apiUrl", "authToken"], (data) => {
      sendResponse({ status: "active", config: data });
    });
    return true; // Keep message channel open for async response
  }
});
