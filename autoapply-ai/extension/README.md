# AutoApply AI Copilot (Chrome Extension)

A Manifest V3 browser extension that brings genuine agentic assistance to **LinkedIn**, **Indeed**, and **Naukri** without scraping or credential handling.

## Core Safety Architecture & Non-Negotiables

1. **Zero Credential Handling**: The extension never prompts for, stores, or transmits your LinkedIn/Indeed/Naukri passwords or session cookies. It operates solely in your own active browser tab that you have already logged into.
2. **Explicit Single-Click Apply**: There is **no batch or unattended auto-submitting**. Every application requires a clear, explicit human click in the moment.
3. **Transparent 4-Step Approval Flow**:
   - **Extract**: Reads live job title, company, and full requirements directly from page DOM.
   - **Prepare**: Analyzes visible form fields with the backend field-mapping heuristics.
   - **Review**: Displays proposed values (name, email, phone, tailored cover letter snippet) inline in the floating panel for you to inspect and edit.
   - **Fill & Apply**: Autofills the form in your active tab. You verify the filled page and click "Apply Now".
4. **Synced Dashboard Tracker**: Every application event (`prepared`, `filled`, `applied`) automatically syncs to your central AutoApply AI dashboard tagged `source: "extension"`.

---

## How to Install (Developer / Unpacked Mode)

1. Open Google Chrome (or Brave / Edge / Arc).
2. Navigate to `chrome://extensions/` in your address bar.
3. Toggle on **Developer mode** in the top-right corner.
4. Click **Load unpacked** in the top-left corner.
5. Select the `autoapply-ai/extension` folder from your repository.
6. The **AutoApply AI Copilot** icon will appear in your browser toolbar!

---

## Connecting to Your Local Backend

1. Make sure your AutoApply AI backend is running:
   ```bash
   run_backend.bat
   ```
2. Click the AutoApply extension icon in your browser toolbar.
3. Verify the API Endpoint is set to `http://127.0.0.1:8000`.
4. Log into the AutoApply AI web app (`http://127.0.0.1:3000`), copy your access token (from localStorage or Profile), and paste it into the extension popup.
5. Click **Save & Sync Connection**. You should see a green dot indicating **Connected to AutoApply Backend**.

---

## Using Copilot on Job Sites

1. Open any job posting on:
   - [LinkedIn Jobs](https://www.linkedin.com/jobs/)
   - [Indeed](https://www.indeed.com/)
   - [Naukri](https://www.naukri.com/)
2. The sleek, dark **AutoApply Copilot** floating panel will appear on the top right.
3. View your real-time **ATS Match Score** and matched vs. missing keywords.
4. Click **Prepare Application** -> inspect and edit proposed field values -> click **Fill Form on Page** -> verify on page and click **Apply Now**!
