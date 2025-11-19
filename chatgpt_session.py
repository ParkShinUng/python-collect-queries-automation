import re
import asyncio

from helper import log
from config import Config
from playwright.async_api import Page
from typing import List, Tuple, Optional, Dict, Any


class ChatGPTSession:
    """하나의 Page(탭) 처리 클래스"""

    def __init__(self, page: Page, cfg: Config, worker_id: int):
        self.page = page
        self.cfg = cfg
        self.worker_id = worker_id

    # ---------- 공통 동작 ----------
    async def go_to_main_url(self) -> None:
        await self.page.goto(self.cfg.chatgpt_url, wait_until="load")

    # ---------- 네트워크 응답 핸들러 ----------
    async def _wait_for_session_code_and_queries(
        self,
        total_timeout: float,
    ) -> Tuple[Optional[str], Optional[List[Any]]]:
        """
        returns:
          (session_code, queries_list)
        """
        session_code: Optional[str] = None
        queries_data: Optional[List[Any]] = None

        async def on_response(response):
            nonlocal session_code, queries_data

            if queries_data is not None:
                return

            url = response.url

            # chatgpt / openai 관련 응답만
            if "chatgpt.com" not in url and "openai.com" not in url:
                return

            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return

            try:
                data = await response.json()
            except Exception:
                return

            if not isinstance(data, dict):
                return

            # 1) location_href → session_code
            if session_code is None and "location_href" in data:
                session_url = str(data["location_href"])
                sc = self.extract_session_code_from_url(session_url)
                if sc:
                    session_code = sc
                    log(f"[Worker {self.worker_id}] session_detect: {session_url} → {session_code}")

            # 2) queries 처리
            if "queries" in data:
                if session_code is not None and session_code in url:
                    queries_data = data["queries"]

        self.page.on("response", on_response)

        waited = 0.0
        interval = 0.5
        try:
            while waited < total_timeout:
                if queries_data is not None:
                    break
                await asyncio.sleep(interval)
                waited += interval
        finally:
            self.page.off("response", on_response)

        return session_code, queries_data

    async def _wait_for_queries_with_known_session(
        self,
        session_code: Optional[str],
        total_timeout: float,
    ) -> Optional[List[Any]]:
        """
        이미 session_code를 알고 있을 때,
        해당 코드가 URL에 포함된 'queries' 응답만 기다려서 반환.
        """
        holder: Dict[str, Optional[List[Any]]] = {"data": None}

        async def on_response(response):
            if holder["data"] is not None:
                return

            url = response.url

            if session_code and session_code not in url:
                return

            if "chatgpt.com" not in url and "openai.com" not in url:
                return

            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return

            try:
                data = await response.json()
            except Exception:
                return

            if isinstance(data, dict) and "queries" in data:
                holder["data"] = data["queries"]

        self.page.on("response", on_response)

        waited = 0.0
        interval = 0.5
        try:
            while waited < total_timeout:
                if holder["data"] is not None:
                    break
                await asyncio.sleep(interval)
                waited += interval
        finally:
            self.page.off("response", on_response)

        return holder["data"]

    # ---------- 프롬프트 전송 & queries 수집 ----------
    async def send_prompt_and_get_session_and_queries(self, prompt: str) -> Tuple[Optional[str], Optional[List[Any]]]:
        await self.page.locator("textarea[data-qa='prompt-textarea']").wait_for(state="visible", timeout=15000)
        await self.page.locator("textarea[data-qa='prompt-textarea']").fill(prompt)

        # 응답 감지 태스크 먼저 생성 후 클릭
        session_queries_task = asyncio.create_task(
            self._wait_for_session_code_and_queries(self.cfg.queries_wait_timeout)
        )

        await self.page.locator("button[data-testid='send-button']").click()
        await self.page.wait_for_timeout(self.cfg.min_answer_wait * 1000)

        session_code, queries = await session_queries_task
        log(f"[Worker {self.worker_id}] send_prompt: session_code={session_code}, "
            f"queries_found={queries is not None}")
        return session_code, queries

    async def reload_and_get_queries(self, session_code: Optional[str]) -> Optional[List[Any]]:
        log(f"[Worker {self.worker_id}] reload: session_code={session_code}")
        task = asyncio.create_task(
            self._wait_for_queries_with_known_session(
                session_code,
                self.cfg.reload_wait_timeout,
            )
        )

        await self.page.reload(wait_until="load")
        return await task

    def extract_session_code_from_url(url: str) -> Optional[str]:
        m = re.search(r"/c/([0-9a-fA-F\-]+)", url)
        if m:
            return m.group(1)
        return None
    

async def chatgpt_login(page: Page, user_id: str, user_pw: str) -> None:
    """ChatGPT 로그인 처리."""
    await page.locator('button[data-testid="login-button"]').click()
    await page.locator('input[id="email"]').fill(user_id)
    await page.locator('button[type="submit"]').click()

    await page.locator('input[name="current-password"]').fill(user_pw)
    await page.locator('button[type="submit"]').click()