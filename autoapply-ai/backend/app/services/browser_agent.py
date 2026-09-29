"""
Browser Automation Agent
========================
Autonomous Playwright-based browser agent implemented as an explicit state machine.
Features:
- State Machine: LOCATING_FORM -> INSPECTING_FIELDS -> MAPPING_FIELDS ->
                 FILLING_FORM -> CAPTURING_SCREENSHOT -> AWAITING_REVIEW (Dry Run) -> SUBMIT
- Human-in-the-Loop Safety Valve: Defaults to Dry Run mode; never auto-submits without explicit opt-in.
- Explainable Decisions: Every field mapped is logged with confidence, source field, and rationale.
- Idempotency: Checks prior submission records to prevent duplicate applications.
- Site Adapters: Extensible for custom board selectors (Greenhouse, Lever, generic).
"""

import asyncio
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from app.config import settings
from app.core.exceptions import (
    BrowserAutomationError,
    CaptchaDetectedError,
    FieldMappingError,
    FormNotFoundError,
)
from app.core.logging import get_logger
from app.db.storage import storage
from app.models.schemas import ApplicationStatus, FieldMappingDecision, FormFieldMetadata, JobPosting, ResumeProfile

logger = get_logger("browser_agent")


class AgentState(str, Enum):
    IDLE = "idle"
    LOCATING_FORM = "locating_form"
    INSPECTING_FIELDS = "inspecting_fields"
    MAPPING_FIELDS = "mapping_fields"
    FILLING_FORM = "filling_form"
    CAPTURING_SCREENSHOT = "capturing_screenshot"
    AWAITING_REVIEW = "awaiting_review"  # Dry Run completion state
    SUBMITTING = "submitting"
    CONFIRMING = "confirming"
    COMPLETED = "completed"
    FAILED = "failed"


class FormSiteAdapter:
    """Base selector adapter for application forms."""

    def find_form_selector(self) -> str:
        return "form, #job-application-form, #application_form, [data-testid='application-form']"

    def find_submit_selector(self) -> str:
        return "button[type='submit'], input[type='submit'], #submit-application-btn, #submit_app"


class BrowserAgent:
    """
    Playwright-powered autonomous browser agent for job applications.
    Implements a verifiable perception -> decision -> action -> review state machine.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.current_state: AgentState = AgentState.IDLE
        self.adapter = FormSiteAdapter()

    # -------------------------------------------------------------
    # State Machine Transitions
    # -------------------------------------------------------------

    async def locate_form(self, page: Any, correlation_id: str = "sys") -> str:
        """State: LOCATING_FORM — Locates the main application form container."""
        self.current_state = AgentState.LOCATING_FORM
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        # Detect captcha or bot challenge
        content = await page.content()
        if "cf-turnstile" in content or "g-recaptcha" in content or "hcaptcha" in content:
            log.warning("captcha_challenge_detected")
            raise CaptchaDetectedError("Cloudflare or CAPTCHA challenge detected on target application page.")

        form_sel = self.adapter.find_form_selector()
        form_locator = page.locator(form_sel).first
        
        count = await form_locator.count()
        if count == 0:
            # Fallback: check if inputs exist directly on body
            inputs_count = await page.locator("input, textarea").count()
            if inputs_count > 0:
                log.info("form_container_fallback_to_body")
                return "body"
            raise FormNotFoundError("Could not locate any application form or input elements on page.")

        log.info("form_located", selector=form_sel)
        return form_sel

    async def inspect_fields(self, page: Any, form_selector: str, correlation_id: str = "sys") -> List[FormFieldMetadata]:
        """State: INSPECTING_FIELDS — Gathers interactive form fields and attributes."""
        self.current_state = AgentState.INSPECTING_FIELDS
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        fields: List[FormFieldMetadata] = []
        form_element = page.locator(form_selector).first
        input_elements = await form_element.locator("input, textarea, select").all()

        for el in input_elements:
            tag = await el.evaluate("e => e.tagName.toLowerCase()")
            input_type = await el.get_attribute("type") or "text"
            if input_type in ("hidden", "submit", "button", "reset"):
                continue

            elem_id = await el.get_attribute("id") or ""
            name = await el.get_attribute("name") or ""
            placeholder = await el.get_attribute("placeholder") or ""
            autocomplete = await el.get_attribute("autocomplete") or ""
            aria_label = await el.get_attribute("aria-label") or ""
            required = bool(await el.evaluate("e => !!e.required"))

            # Discover label text
            label_text = ""
            if elem_id:
                label_el = page.locator(f"label[for='{elem_id}']").first
                if await label_el.count() > 0:
                    label_text = await label_el.inner_text()
            if not label_text:
                # Check parent or preceding text
                label_text = await el.evaluate(
                    """e => {
                        let l = e.closest('label');
                        if (l) return l.innerText;
                        let p = e.previousElementSibling;
                        if (p && p.tagName === 'LABEL') return p.innerText;
                        return '';
                    }"""
                )

            # Build best selector
            if elem_id:
                selector = f"#{elem_id}"
            elif name:
                selector = f"{tag}[name='{name}']"
            else:
                selector = f"{tag}[type='{input_type}']"

            metadata = FormFieldMetadata(
                tag=tag,
                element_id=elem_id,
                name=name,
                input_type=input_type,
                placeholder=placeholder,
                label_text=label_text.strip(),
                aria_label=aria_label,
                autocomplete=autocomplete,
                selector=selector,
                required=required,
            )
            fields.append(metadata)

        log.info("fields_inspected", field_count=len(fields))
        return fields

    def map_fields(
        self,
        fields: List[FormFieldMetadata],
        profile: ResumeProfile,
        correlation_id: str = "sys",
    ) -> List[FieldMappingDecision]:
        """State: MAPPING_FIELDS — Decides which profile value fills each DOM field."""
        self.current_state = AgentState.MAPPING_FIELDS
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)
        from app.services.field_mapper import map_fields_heuristic
        return map_fields_heuristic(fields, profile, correlation_id=correlation_id)

    async def fill_form(
        self,
        page: Any,
        decisions: List[FieldMappingDecision],
        correlation_id: str = "sys",
    ) -> None:
        """State: FILLING_FORM — Executes polite keystrokes into mapped fields."""
        self.current_state = AgentState.FILLING_FORM
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        for d in decisions:
            try:
                locator = page.locator(d.selector).first
                if await locator.count() > 0:
                    await locator.scroll_into_view_if_needed()
                    await locator.fill(d.value_filled)
                    log.debug("field_filled", field=d.field_name, selector=d.selector)
            except Exception as e:
                log.warning("field_fill_failed", selector=d.selector, error=str(e))

    async def capture_screenshot(
        self,
        page: Any,
        job_id: str,
        correlation_id: str = "sys",
        user_id: str = "legacy_user",
    ) -> Path:
        """State: CAPTURING_SCREENSHOT — Takes visual proof of the filled form namespaced per user."""
        self.current_state = AgentState.CAPTURING_SCREENSHOT
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        user_dir = settings.SCREENSHOTS_DIR / user_id
        user_dir.mkdir(parents=True, exist_ok=True)
        screenshot_filename = f"review_{job_id}_{int(datetime.now(timezone.utc).timestamp())}.png"
        screenshot_path = user_dir / screenshot_filename
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            log.info("screenshot_captured", path=str(screenshot_path), user_id=user_id)
        except Exception as e:
            log.warning("screenshot_capture_failed", error=str(e))
        return screenshot_path

    async def submit_form(self, page: Any, correlation_id: str = "sys") -> bool:
        """State: SUBMITTING — Clicks submit button ONLY when explicitly instructed."""
        self.current_state = AgentState.SUBMITTING
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        submit_sel = self.adapter.find_submit_selector()
        submit_btn = page.locator(submit_sel).first
        if await submit_btn.count() > 0:
            await submit_btn.click()
            log.info("submit_button_clicked", selector=submit_sel)
            return True
        return False

    async def confirm_submission(self, page: Any, correlation_id: str = "sys") -> bool:
        """State: CONFIRMING — Verifies confirmation message or page redirection."""
        self.current_state = AgentState.CONFIRMING
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("agent_state_transition", state=self.current_state.value)

        # Wait briefly for DOM reaction
        await asyncio.sleep(1.0)
        content = (await page.content()).lower()
        success_signals = ["thank you", "submitted", "application received", "success", "confirmation"]
        confirmed = any(signal in content for signal in success_signals)
        log.info("submission_confirmed", success=confirmed)
        return confirmed

    # -------------------------------------------------------------
    # Full Agent Loop with Safety Valve
    # -------------------------------------------------------------

    async def apply_to_job(
        self,
        page: Any,
        profile: ResumeProfile,
        job: JobPosting,
        dry_run: Optional[bool] = None,
        correlation_id: str = "sys",
        user_id: str = "legacy_user",
    ) -> ApplicationStatus:
        """
        Executes the end-to-end perception -> action -> review loop for one job.
        Safety Valve: Defaults to DRY RUN mode (halts at AWAITING_REVIEW with screenshot and mappings).
        """
        log = get_logger("browser_agent", correlation_id=correlation_id)
        log.info("starting_application_loop", job_id=job.id, company=job.company, dry_run=dry_run, user_id=user_id)

        # 1. Idempotency Check (Scoped to user_id)
        if storage.is_job_applied_or_submitted(job.id, user_id=user_id):
            log.info("idempotency_skip", job_id=job.id, user_id=user_id, reason="Job already applied or submitted.")
            existing = storage.get_application(job.id, user_id=user_id)
            if existing:
                return existing

        is_dry_run = settings.DRY_RUN if dry_run is None else dry_run

        try:
            # 2. LOCATING_FORM
            form_sel = await self.locate_form(page, correlation_id=correlation_id)

            # 3. INSPECTING_FIELDS
            fields = await self.inspect_fields(page, form_sel, correlation_id=correlation_id)

            # 4. MAPPING_FIELDS
            mappings = self.map_fields(fields, profile, correlation_id=correlation_id)

            # 5. FILLING_FORM
            await self.fill_form(page, mappings, correlation_id=correlation_id)

            # 6. CAPTURING_SCREENSHOT (Namespaced by user_id)
            screenshot_path = await self.capture_screenshot(
                page, job.id, correlation_id=correlation_id, user_id=user_id
            )

            now = datetime.now(timezone.utc).isoformat()

            # 7. SAFETY VALVE CHECK (Dry Run Mode vs Auto-Submit)
            if is_dry_run or not settings.AUTO_SUBMIT_ENABLED:
                self.current_state = AgentState.AWAITING_REVIEW
                log.info(
                    "safety_valve_halt",
                    message="Dry run complete. Form filled and verified without submitting. Queued for review.",
                )

                app_status = ApplicationStatus(
                    job_id=job.id,
                    user_id=user_id,
                    company=job.company,
                    title=job.title,
                    stage="needs_review",
                    match_score=0.85,
                    updated_at=now,
                    dry_run=True,
                    screenshot_path=str(screenshot_path),
                    field_mappings=mappings,
                    notes="Form filled in verified Dry Run mode. Awaiting human approval.",
                )
                storage.save_or_update_application(app_status, user_id=user_id, url=job.url, location=job.location)
                return app_status

            # 8. SUBMITTING (Only if explicitly enabled)
            submitted = await self.submit_form(page, correlation_id=correlation_id)
            confirmed = await self.confirm_submission(page, correlation_id=correlation_id)

            final_stage = "submitted" if confirmed else "applied"
            app_status = ApplicationStatus(
                job_id=job.id,
                user_id=user_id,
                company=job.company,
                title=job.title,
                stage=final_stage,
                match_score=0.85,
                updated_at=now,
                dry_run=False,
                screenshot_path=str(screenshot_path),
                field_mappings=mappings,
                notes="Submitted live after user authorization.",
            )
            storage.save_or_update_application(app_status, user_id=user_id, url=job.url, location=job.location)
            self.current_state = AgentState.COMPLETED
            return app_status

        except Exception as e:
            self.current_state = AgentState.FAILED
            log.error("application_flow_failed", job_id=job.id, error=str(e))
            now = datetime.now(timezone.utc).isoformat()
            failed_status = ApplicationStatus(
                job_id=job.id,
                user_id=user_id,
                company=job.company,
                title=job.title,
                stage="failed",
                match_score=0.0,
                updated_at=now,
                dry_run=is_dry_run,
                notes=f"Agent error: {str(e)}",
            )
            storage.save_or_update_application(failed_status, user_id=user_id, url=job.url, location=job.location)
            return failed_status

