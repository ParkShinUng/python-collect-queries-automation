import asyncio

from helper import log
from chatgpt_session import ChatGPTSession
from typing import List, Tuple, Optional, Any


async def worker_job(
    session: ChatGPTSession,
    jobs: List[Tuple[int, str]],
) -> List[Tuple[int, str]]:
    """
    각 탭에서 자기에게 할당된 (row, prompt) 리스트를 순차 처리.
    결과로 (row, formatted_queries) 리스트 반환.
    """
    results: List[Tuple[int, str]] = []

    await session.go_to_main_url()

    for row, prompt_text in jobs:
        log(f"[Worker {session.worker_id}] Row: {row} 처리 중 Prompt: {prompt_text}")
        queries: Optional[str] = None

        # 1차: 프롬프트 전송 후 session_code + queries 수집
        try:
            queries = await session.send_prompt_and_get_session_and_queries(prompt_text)
        except Exception as e:
            log(f"[Worker {session.worker_id}] Row: {row}, Prompt: {prompt_text}, 1차 수집 중 예외: {e}")

        # 2차: queries 없으면, session_code 기준으로 새로고침 재시도
        attempt = 0
        while (not queries) and attempt < session.cfg.max_reload_try:
            attempt += 1
            log(f"[Worker {session.worker_id}] Row: {row}, Prompt: {prompt_text}, queries 없음 → "
                f"새로고침 재시도 {attempt}/{session.cfg.max_reload_try}")
            try:
                queries = await session.reload_and_get_queries()
            except Exception as e:
                log(f"[Worker {session.worker_id}] Row: {row}, Prompt: {prompt_text}, 새로고침 중 예외: {e}")

        if not queries:
            queries = "X"
        log(f"[Worker {session.worker_id}] Row: {row}, Prompt: {prompt_text}, 결과: {queries}")

        results.append((row, queries))

        await asyncio.sleep(session.cfg.between_prompts_sleep)

    return results