# AutoApply AI — Security Architecture & Policy

## 1. Security Overview & Philosophy

AutoApply AI is designed with an uncompromising safety-first architecture. Because the system automates browser interactions on behalf of candidates, strict guardrails are enforced at every layer to prevent unauthorized form submission, credential leakage, cross-tenant data exposure, or automated spamming.

---

## 2. Core Safety Guarantees (Non-Negotiable)

1. **Immutable Dry-Run Default**:
   `DRY_RUN=True` and `AUTO_SUBMIT_ENABLED=False` are hardcoded defaults across all user accounts.
2. **Mandatory Human-in-the-Loop Halt**:
   The Playwright automation state machine (`LOCATING_FORM → INSPECTING_FIELDS → MAPPING_FIELDS → FILLING_FORM → CAPTURING_SCREENSHOT → AWAITING_REVIEW → SUBMITTING`) unconditionally halts at `AWAITING_REVIEW`.
   - The browser agent captures a high-resolution screenshot.
   - It outputs per-field mapping confidence percentages and transparent decision rationales.
   - Forms are never submitted live without explicit, authenticated human interaction (`auto_submit_override=True` on a per-action basis).
3. **Respectful Web Automation**:
   - `robots.txt` compliance is evaluated before every scrape request.
   - Crawl-delay limits are observed with jitter to prevent server degradation.
   - Job listings are content-hashed (SHA-256) to eliminate redundant crawling and duplicate applications.

---

## 3. Authentication & Multi-Tenant Data Isolation

### Password Security
- Passwords are never stored or logged in plaintext.
- Hashing is performed using **bcrypt** with secure per-user salt generation.
- Login endpoints enforce generic error messages to prevent account enumeration.
- Sliding-window in-memory rate limiting throttles brute-force attempts on `/api/auth/login` and `/api/auth/signup`.

### Session & Token Management
- Authentication relies on standards-compliant JSON Web Tokens (**JWT**).
- Short-lived **access tokens** (default 60 minutes) are signed using HMAC-SHA256 with a high-entropy secret (`JWT_SECRET`).
- Supports both `Authorization: Bearer <token>` headers and secure `httpOnly`, `SameSite=Lax` cookies.
- Refresh tokens allow seamless credential renewal without re-entering credentials.

### Tenant Isolation
- Every database entity (`applications`, `user_profiles`, `resumes`, `agent_status`, `password_resets`) is explicitly keyed by foreign key `user_id`.
- Application queries strictly enforce `WHERE user_id = :user_id`.
- User A cannot access, view, approve, or reject applications created by User B (verified in integration test suite `tests/test_api_routes.py::test_multi_tenant_data_isolation`).
- Resume uploads are isolated in user-specific storage paths (`data/resumes/{user_id}/`).
- Form screenshots are isolated in user-specific directories (`data/screenshots/{user_id}/`) and served exclusively via authenticated, tenant-verified endpoints (`GET /api/screenshots/{job_id}`).

---

## 4. Secrets Management & KMS Upgrade Path

### Current Local Architecture: `LocalEncryptedSecretsManager`
In development and standalone deployments, third-party ATS credentials and API keys are protected using Fernet symmetric encryption:
- Encryption algorithm: **AES-128 in CBC mode** with PKCS7 padding.
- Authentication: **HMAC-SHA256** using keys derived via PBKDF2-HMAC-SHA256 with 100,000 iterations.
- Salt: Cryptographically random 16-byte salt per ciphertext.
- Master Key: Loaded from `SECRET_KEY` environment variable. In `ENV=production`, server startup fails immediately if a default or weak placeholder key is detected.

### Enterprise KMS Upgrade Roadmap
The `SecretsManager` interface is pluggable by design:
```
                       ┌───────────────────────────────┐
                       │    SecretsManagerInterface    │
                       └──────────────┬────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
┌───────▼────────────────┐   ┌────────▼───────────────┐   ┌─────────▼───────────────┐
│ LocalEncryptedManager  │   │ HashiCorp VaultAdapter │   │ AWS KMS / GCP KMS       │
│ (AES-128-CBC + Fernet) │   │ (AppRole / Transit Eng)│   │ (Envelope Encryption)   │
└────────────────────────┘   └────────────────────────┘   └─────────────────────────┘
```
For production cloud deployments:
1. **HashiCorp Vault**: Utilize the Vault Transit Secret Engine for envelope encryption without persisting keys on disk.
2. **AWS KMS / GCP Cloud KMS**: Integrate managed hardware security modules (HSM) with IAM-governed key rotation policies.

---

## 5. PII & Logging Controls

- **Zero PII Logging**: Structured logging (`structlog`) strips resume contents, emails, phone numbers, and candidate names from system logs.
- **Correlation Tracking**: Every request generates a non-identifying trace `correlation_id` attached to log lines for observability without violating privacy.
- **Upload Constraints**: Resume files are enforced with strict size limits (15MB maximum) and MIME/type validation (`.pdf`, `.docx`, `.txt`).

---

## 6. Reporting a Security Vulnerability

If you discover a security vulnerability within AutoApply AI, please do not file a public GitHub issue.

Please report vulnerabilities privately via email to:
**security@autoapply.local** (or the project maintainer).

Include:
- Type of vulnerability (e.g., cross-tenant exposure, auth bypass, injection)
- Step-by-step reproduction instructions or proof-of-concept
- Impact assessment

We commit to acknowledging your report within 48 hours and providing a target remediation timeline.
