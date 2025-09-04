from browser import BrowserAgent, BrowserActionType
from playwright.sync_api import sync_playwright
from PIL import Image
from io import BytesIO
from browser import BrowserAgent,ActionPlanner,SimplePlanner
from anthropicAgent import AnthropicPlanner
import os
import time

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


def main():
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()
            page = context.new_page()
            goal1="give me the wikipedia page of MCP"

            ba = BrowserAgent(page=page,context=context,action_planner=AnthropicPlanner(),goal=goal1)
            ba.page.goto("https://google.com")
            # bs=ba.get_state()
            ba.start()
    finally:
        time.sleep(5)
        browser.close()

if __name__ == "__main__":
    
    main()

