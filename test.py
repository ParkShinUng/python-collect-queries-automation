import asyncio

from config import Config
from playwright.async_api import async_playwright, Page

cfg = Config()

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch_persistent_context(
            cfg.user_data_dir,
            headless=cfg.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.pages[0]
        await page.goto(cfg.chatgpt_url, wait_until="load")
        
        # 로그인 처리
        await page.locator('button[data-testid="login-button"]').click()
        await page.locator('input[id="email"]').fill(cfg.USER_ID)
        await page.locator('button[type="submit"]').click()
        
        await page.locator('input[name="current-password"]').fill(cfg.USER_PW)
        await page.locator('button[type="submit"]').click()
        return
        
        
asyncio.run(run())