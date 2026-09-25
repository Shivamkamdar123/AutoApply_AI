"""
Fixture Replay Test Harness for Browser Agent
==============================================
Tests the Playwright browser agent against local HTML form fixtures.
Ensures reproducible, stable CI testing without depending on real external websites.
"""

from pathlib import Path
import pytest
from playwright.async_api import async_playwright

from app.config import settings
from app.models.schemas import JobPosting, ResumeProfile
from app.services.browser_agent import AgentState, BrowserAgent


@pytest.fixture
def replay_profile() -> ResumeProfile:
    return ResumeProfile(
        full_name="Sarah Connor",
        email="sarah.connor@example.com",
        phone="+1 (555) 987-6543",
        skills=["python", "fastapi", "docker", "postgresql"],
        years_experience=5.0,
        raw_text="Experienced engineer skilled in Python and FastAPI.",
    )


@pytest.fixture
def test_job() -> JobPosting:
    return JobPosting(
        id="fixture-job-001",
        title="Senior Python Backend Engineer",
        company="Cyberdyne Systems",
        location="Remote",
        description="Python, FastAPI, Docker microservices.",
        url="https://example.com/careers/job-001",
        source="fixture",
    )


@pytest.mark.asyncio
async def test_standard_form_replay_dry_run(replay_profile: ResumeProfile, test_job: JobPosting):
    """
    Test end-to-end replay on standard HTML form fixture in dry-run mode:
    Locate -> Inspect -> Map -> Fill -> Screenshot -> Halt at Review.
    """
    fixture_path = settings.FIXTURES_DIR / "standard_job_form.html"
    assert fixture_path.exists(), f"Fixture file not found: {fixture_path}"

    fixture_url = fixture_path.as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(fixture_url)

        agent = BrowserAgent(headless=True)

        # Execute application loop in default dry-run mode
        status = await agent.apply_to_job(page, replay_profile, test_job, dry_run=True)

        # 1. Verify safety valve state: stopped before submit
        assert status.stage == "needs_review"
        assert status.dry_run is True
        assert agent.current_state == AgentState.AWAITING_REVIEW

        # 2. Verify form inputs in DOM were correctly filled
        name_val = await page.locator("#applicant_name").input_value()
        email_val = await page.locator("#applicant_email").input_value()
        phone_val = await page.locator("#applicant_phone").input_value()
        exp_val = await page.locator("#applicant_experience").input_value()

        assert name_val == "Sarah Connor"
        assert email_val == "sarah.connor@example.com"
        assert "555" in phone_val
        assert "5" in exp_val

        # 3. Verify submit was NOT triggered (success message still hidden)
        is_success_visible = await page.locator("#success").is_visible()
        assert is_success_visible is False

        # 4. Verify field mapping decisions logged with rationales
        assert len(status.field_mappings) >= 4
        for mapping in status.field_mappings:
            assert mapping.confidence >= 0.80
            assert len(mapping.rationale) > 0
            assert mapping.value_filled is not None

        # 5. Verify screenshot was created
        if status.screenshot_path:
            assert Path(status.screenshot_path).exists()

        await browser.close()


@pytest.mark.asyncio
async def test_greenhouse_form_replay_split_names(replay_profile: ResumeProfile):
    """
    Test Greenhouse-style form with split first/last name fields.
    """
    fixture_path = settings.FIXTURES_DIR / "greenhouse_job_form.html"
    fixture_url = fixture_path.as_uri()

    job = JobPosting(
        id="fixture-gh-002",
        title="Software Engineer",
        company="Greenhouse Corp",
        location="Remote",
        description="FastAPI developer",
        url="https://example.com/careers/gh-002",
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(fixture_url)

        agent = BrowserAgent(headless=True)
        status = await agent.apply_to_job(page, replay_profile, job, dry_run=True)

        assert status.stage == "needs_review"

        first_val = await page.locator("#first_name").input_value()
        last_val = await page.locator("#last_name").input_value()
        email_val = await page.locator("#email").input_value()

        assert first_val == "Sarah"
        assert last_val == "Connor"
        assert email_val == "sarah.connor@example.com"

        await browser.close()
