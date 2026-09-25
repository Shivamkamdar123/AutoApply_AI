"""
End-to-End Pipeline Integration Test
=====================================
Validates the complete autonomous flow:
1. Parse resume file
2. Scrape/source job postings
3. Score & rank matches
4. Drive browser agent (perception -> mapping -> filling -> screenshot)
5. Enforce human-in-the-loop review queue
6. Record persistent idempotent application state
"""

from pathlib import Path
import pytest
from playwright.async_api import async_playwright

from app.config import settings
from app.db.storage import storage
from app.models.schemas import ApplicationStatus, ReviewActionRequest
from app.services.browser_agent import AgentState, BrowserAgent
from app.services.job_scraper import get_jobs
from app.services.matcher import rank_jobs
from app.services.resume_parser import parse_resume


@pytest.mark.asyncio
async def test_full_pipeline_end_to_end(sample_txt_resume: Path):
    """
    Simulates a full production cycle:
    Upload Resume -> Match Jobs -> Draft Application via Playwright -> Human Review -> Verification.
    """
    # Step 1: Parse candidate resume
    profile = parse_resume(str(sample_txt_resume), correlation_id="e2e-run")
    assert profile.full_name == "Jane Doe"
    assert "fastapi" in profile.skills

    # Step 2: Sourcing job postings
    jobs = get_jobs(query="python", limit=5, correlation_id="e2e-run")
    assert len(jobs) > 0

    # Step 3: Match and rank jobs
    matches = rank_jobs(profile, jobs, correlation_id="e2e-run")
    assert len(matches) > 0
    top_match = matches[0]
    assert top_match.score > 0.0

    # Step 4: Autonomous Browser Agent action against HTML fixture
    fixture_url = (settings.FIXTURES_DIR / "standard_job_form.html").as_uri()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(fixture_url)

        agent = BrowserAgent(headless=True)
        
        # Executes perception -> field mapping -> form filling -> screenshot -> dry run halt
        app_status = await agent.apply_to_job(
            page=page,
            profile=profile,
            job=top_match.job,
            dry_run=True,
            correlation_id="e2e-run",
        )

        assert app_status.stage == "needs_review"
        assert app_status.dry_run is True
        assert len(app_status.field_mappings) >= 3
        assert agent.current_state == AgentState.AWAITING_REVIEW

        await browser.close()

    # Step 5: Verify persistent record in SQLite
    saved = storage.get_application(top_match.job.id)
    assert saved is not None
    assert saved.stage == "needs_review"

    # Step 6: Human-in-the-Loop Approval Action
    saved.stage = "applied"
    saved.notes = "Approved by human reviewer in verified dry-run mode."
    storage.save_or_update_application(saved)

    # Step 7: Verify idempotency - cannot re-apply to already applied job
    assert storage.is_job_applied_or_submitted(top_match.job.id) is True
