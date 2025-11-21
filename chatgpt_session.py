import re
import time
import asyncio

from operator import eq
from helper import log
from config import Config
from urllib.parse import urljoin
from playwright.async_api import Page
from jsonpath_ng import parse
from typing import List, Tuple, Optional, Any


class ChatGPTSession:
    """하나의 Page(탭) 처리 클래스"""

    def __init__(self, page: Page, cfg: Config, worker_id: int):
        self.page = page
        self.cfg = cfg
        self.worker_id = worker_id
        self.session_code = None

    # ---------- 공통 동작 ----------

    # ---------- 네트워크 응답 핸들러 ----------
    async def _wait_for_session_code_and_queries(
        self,
        total_timeout: float,
    ) -> Optional[str]:
        """
        returns:
          queries: Optional[str])
        """
        queries_data: Optional[str] = None

        async def on_response(response):
            nonlocal queries_data

            if queries_data is not None:
                return
            
            if (self.session_code is None) or (self.session_code not in response.url):
                return
            
            # chatgpt / openai 관련 응답만
            target_url = urljoin(self.cfg.check_json_url, self.session_code)
            if target_url != response.url:
                return

            content_type = response.headers.get("content-type", "")
            if "application/json" not in content_type:
                return

            data = await response.json()
            
            jsonpath_expr = parse("$..queries")
            find_data_list = jsonpath_expr.find(data)
            
            if not find_data_list:
                return

            new_queries_data_list = [query_str for find_data in find_data_list for query_str in find_data.value]
            queries_data = ', '.join(new_queries_data_list)

        self.page.on("response", on_response)

        waited = 0.0
        interval = 0.1
        try:
            while waited < total_timeout:
                if queries_data is not None:
                    break
                await asyncio.sleep(interval)
                waited += interval
        finally:
            self.page.remove_listener('response', on_response)
            print(f"{self.prompt} : {queries_data}")

        return queries_data

    # ---------- 프롬프트 전송 & queries 수집 ----------
    async def send_prompt_and_get_session_and_queries(self, prompt: str) -> Tuple[Optional[str], Optional[List[Any]]]:        
        prompt_textarea = await self.page.wait_for_selector("div[id='prompt-textarea']")
        await prompt_textarea.fill(prompt)
        await prompt_textarea.press("Enter")
        await self.page.wait_for_url("**/c/*", timeout=self.cfg.min_answer_wait * 1000)

        self.session_code = self.extract_session_code_from_url(await self.page.evaluate("location.href"))

        # 응답 감지 태스크 먼저 생성 후 클릭
        session_queries_task = asyncio.create_task(
            self._wait_for_session_code_and_queries(self.cfg.queries_wait_timeout)
        )

        queries = await session_queries_task
        log(f"[Worker {self.worker_id}] send_prompt={prompt} session_code={self.session_code}, "
            f"queries_found={queries is not None}")
        
        await asyncio.sleep(self.cfg.min_answer_wait)
        await self.delete_chat()
        
        return queries

    async def reload_and_get_queries(self) -> Optional[List[Any]]:
        log(f"[Worker {self.worker_id}] reload: session_code={self.session_code}")
        task = asyncio.create_task(
            self._wait_for_session_code_and_queries(self.cfg.reload_wait_timeout)
        )
        await self.page.reload(wait_until="load")
        return await task
    
    async def delete_chat(self) -> None:
        await self.page.locator('button[data-testid="conversation-options-button"]').click()
        await self.page.locator('text=삭제').click()
        await self.page.locator('button[data-testid="delete-conversation-confirm-button"]').click()
        await asyncio.sleep(self.cfg.between_prompts_sleep)
    
    @staticmethod
    def extract_session_code_from_url(url: str) -> Optional[str]:
        m = re.search(r"/c/([0-9a-fA-F\-]+)", url)
        if m:
            return m.group(1)
        return None
    