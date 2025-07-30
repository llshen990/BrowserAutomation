from playwright.async_api import async_playwright,Playwright
import asyncio

async def launch_async():
    # Start Playwright
    async with async_playwright() as p:
        # Launch a Chromium browser (set headless=False to see the window)
        # chr=p.chromium
        # browser = await chr.launch(headless=False)
        browser = await p.chromium.launch(headless=False)
        # Create a new context (isolated browser profile)
        context = await browser.new_context()
        # Open a new page (tab)
        page = await context.new_page()
        # Navigate to a URL
        await page.goto("https://google.com")
        # Take a screenshot
        await page.screenshot(path="example.png")
        # Clean up
        await browser.close()

if __name__ == "__main__":
    asyncio.run(launch_async())