import asyncio

from helper import log
from chatgpt_session import ChatGPTSession
from typing import List, Tuple, Optional, Any


def format_queries_for_excel(queries: Any) -> str:
    """
    엑셀 기록 규칙:
    - None 또는 빈 데이터: 'X'
    - 1개: 그대로
    - 2개 이상: ','로 join
    """
    if not queries:
        return "X"

    def item_to_str(item: Any) -> str:
        if isinstance(item, dict):
            for key in ("query", "q", "text"):
                if key in item:
                    return str(item[key])
            return str(item)
        return str(item)

    if isinstance(queries, list):
        if len(queries) == 1:
            return item_to_str(queries[0])
        return ",".join(item_to_str(q) for q in queries)

    return str(queries)


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
        log(f"[Worker {session.worker_id}] Row {row} 처리 중: {prompt_text!r}")

        session_code: Optional[str] = None
        queries: Optional[List[Any]] = None

        # 1차: 프롬프트 전송 후 session_code + queries 수집
        try:
            session_code, queries = await session.send_prompt_and_get_session_and_queries(prompt_text)
        except Exception as e:
            log(f"[Worker {session.worker_id}] Row {row} 1차 수집 중 예외: {e}")

        # 2차: queries 없으면, session_code 기준으로 새로고침 재시도
        attempt = 0
        while (not queries) and attempt < session.cfg.max_reload_try:
            attempt += 1
            log(f"[Worker {session.worker_id}] Row {row} queries 없음 → "
                f"새로고침 재시도 {attempt}/{session.cfg.max_reload_try}")
            try:
                queries = await session.reload_and_get_queries(session_code)
            except Exception as e:
                log(f"[Worker {session.worker_id}] Row {row} 새로고침 중 예외: {e}")

        formatted = format_queries_for_excel(queries)
        log(f"[Worker {session.worker_id}] Row {row} 결과: {formatted}")

        results.append((row, formatted))

        # 다음 질문 전환 전에 새 채팅
        try:
            await session.go_to_new_chat()
        except Exception as e:
            log(f"[Worker {session.worker_id}] Row {row} 새 채팅 전환 중 예외: {e}")

        await asyncio.sleep(session.cfg.between_prompts_sleep)

    return results