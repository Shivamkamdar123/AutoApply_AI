"""
Browser automation agent
=========================
STATUS: STUB. This is intentionally not implemented yet.

This is the highest-risk, least-predictable part of the system: it has to
drive a real browser against real, constantly-changing job site layouts.
It cannot be built correctly "blind" — it needs a tight loop of running it
against an actual site, seeing what breaks, and fixing it. That loop is a
normal, expected part of building this kind of agent, not a sign anything
is wrong with the approach.

Build this LAST, after the resume parser, matcher, and dashboard are
solid — those give you something demoable even while this piece is still
rough.

Planned architecture (perceive -> decide -> act loop):

    1. PERCEIVE  - Take a snapshot of the current page: DOM structure
                   and/or a screenshot, plus the current form's fields.
    2. DECIDE    - Feed that snapshot + the candidate's profile to an LLM
                   (or rule-based logic first, LLM later) to decide the
                   next action: fill field X with value Y, click "Next",
                   flag for human review, etc.
    3. ACT       - Execute that action via Playwright.
    4. VERIFY    - Re-check the page to confirm the action worked before
                   moving to the next step (this is what makes it more
                   than "aim and click blindly").
    5. Loop until the application is submitted, a CAPTCHA/login-wall is
       hit (-> escalate to human review), or a retry limit is reached.

Suggested first milestone: get this working end-to-end on ONE site with a
simple, stable form (a test/demo site, not a real job board) before
pointing it at anything live. That proves the loop works before you deal
with real-world messiness.
"""

from app.models.schemas import ResumeProfile, JobPosting


class BrowserAgent:
    """
    Interface for the browser automation layer. Methods raise
    NotImplementedError on purpose — fill these in once Playwright is
    wired up and you have a real page to test against.
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        # TODO: launch Playwright browser/context here.

    def perceive(self, page_url: str) -> dict:
        """Return the current page's relevant structure (form fields, etc.)."""
        raise NotImplementedError("Wire this up with Playwright once you have a target site.")

    def decide_next_action(self, page_state: dict, profile: ResumeProfile, job: JobPosting) -> dict:
        """
        Decide what to do next given the current page and candidate profile.
        Start with simple rule-based logic (e.g. "if field label contains
        'email', fill with profile.email"); upgrade to an LLM call later
        for handling unfamiliar/ambiguous forms.
        """
        raise NotImplementedError

    def act(self, action: dict) -> bool:
        """Execute a single action (fill/click/submit) and return success."""
        raise NotImplementedError

    def apply_to_job(self, profile: ResumeProfile, job: JobPosting) -> str:
        """
        Full loop for one job. Returns a stage string matching
        ApplicationStatus.stage: "applied", "needs_review", or "failed".
        """
        raise NotImplementedError("Browser agent not implemented yet — see module docstring for the plan.")
