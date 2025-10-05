from browser import BrowserAgent, BrowserActionType
from playwright.async_api import async_playwright
from PIL import Image
from io import BytesIO
from browser import BrowserAgent,ActionPlanner
from anthropicAgent import AnthropicPlanner
import os
import time
import asyncio

def main1():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        ba = BrowserAgent(page=page,context=context,action_planner=SimplePlanner(),goal="something")
        ba.page.goto("https://google.com")
        bs=ba.get_state()
        print(type(bs.screenshot))
        print(bs.screenshot[:20])

        
        # ap = AnthropicPlanner()
        # ap1 = ap.screenshot_conversion(bs.screenshot,bs)
        # Image.open(BytesIO(ap1)).show()
        # scrollpos = ba.get_scroll_position()   
        # print(scrollpos)
        mousepos = ba.get_mouse_position()
        print(mousepos)

        status1 = ba.status
        print(status1)


async def main():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()
            goal1="give me the wikipedia page of React"

            ba = BrowserAgent(page=page,context=context,action_planner=AnthropicPlanner(),goal=goal1)
            await ba.page.goto("https://bing.com")
            # bs=ba.get_state()
            await ba.start()
    finally:
        time.sleep(5)
        await browser.close()

if __name__ == "__main__":
    
    asyncio.run(main())

