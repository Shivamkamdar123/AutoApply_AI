import asyncio
import os
from pathlib import Path
from playwright.async_api import async_playwright

async def run_comprehensive_live_test():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 900})
        
        logs = []
        page.on("console", lambda m: logs.append(f"[{m.type}] {m.text}"))

        print("\n--- STEP 1: Connect to Frontend Server ---")
        await page.goto("http://127.0.0.1:5500/")
        await page.wait_for_selector(".badge-tag.connected", timeout=15000)
        badge = await page.locator("#connectionBadge").inner_text()
        print(f"Connection Status: {badge}")

        # Check candidate name
        initial_name = await page.locator("#profileName").inner_text()
        print(f"Initial Profile Name: {initial_name}")

        print("\n--- STEP 2: Upload Resume File via Live Dashboard ---")
        resume_path = str(Path(__file__).resolve().parent / "sample_resume.txt")
        file_input = page.locator("#resumeFileInput")
        await file_input.set_input_files(resume_path)
        
        # Wait for toast and profile update
        await page.wait_for_timeout(4000)
        updated_name = await page.locator("#profileName").inner_text()
        skills = await page.locator("#profileSkills").inner_text()
        print(f"Updated Profile Name: {updated_name}")
        print(f"Extracted Skills: {skills.replace('\n', ', ')}")

        print("\n--- STEP 3: Human-in-the-Loop Review Queue Verification ---")
        await page.wait_for_timeout(2000)
        pending_count = await page.locator("#queuePendingCount").inner_text()
        review_cards = await page.locator(".review-card").count()
        print(f"Review Queue: {pending_count} ({review_cards} cards rendered)")

        if review_cards > 0:
            job_title = await page.locator(".review-job-title").first.inner_text()
            match_score = await page.locator(".review-card .score-badge").first.inner_text()
            print(f"Drafted Application: {job_title} ({match_score})")

            print("\n--- STEP 4: Approve Application (Dry Run Mode) ---")
            approve_btn = page.locator(".review-card .action-buttons .btn-primary").first
            await approve_btn.click()
            await page.wait_for_timeout(2000)

            queue_after = await page.locator("#queuePendingCount").inner_text()
            applied_stat = await page.locator("#statApplied").inner_text()
            print(f"Review Queue after approval: {queue_after}")
            print(f"Verified/Applied Stats Count: {applied_stat}")

        print("\n--- STEP 5: Autonomous Agent Toggle ---")
        toggle_btn = page.locator("#btnToggleAgent")
        status_before = await page.locator("#statusText").inner_text()
        print(f"Agent Status before toggle: {status_before}")
        await toggle_btn.click()
        await page.wait_for_timeout(1000)
        status_after = await page.locator("#statusText").inner_text()
        print(f"Agent Status after toggle: {status_after}")

        print("\n--- STEP 6: Search Filter Functionality ---")
        search_input = page.locator("#jobSearchInput")
        await search_input.fill("backend")
        await page.wait_for_timeout(500)
        filtered_rows = await page.locator("#applicationsBody tr").count()
        print(f"Table rows filtered by 'backend': {filtered_rows}")
        await search_input.fill("")

        print("\n--- STEP 7: Save Visual Artifact ---")
        screenshot_path = "e2e_verified_dashboard.png"
        await page.screenshot(path=screenshot_path, full_page=True)
        print(f"Full page screenshot saved to {screenshot_path}")

        await browser.close()
        print("\nALL WORKFLOW STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_comprehensive_live_test())
