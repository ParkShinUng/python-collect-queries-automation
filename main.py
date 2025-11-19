import asyncio

from helper import log
from pathlib import Path
from typing import List, Tuple
from config import Config
from workers import worker_job
from excel_manager import ExcelManager
from chatgpt_session import ChatGPTSession, chatgpt_login

from playwright.async_api import async_playwright, Page


async def main():
    cfg = Config()
    
    login_success = False

    # ----- 엑셀 로드 및 작업 읽기 -----
    excel_mgr = ExcelManager(cfg)
    
    for sheet_name in excel_mgr.sheet_list:
        excel_mgr.ws = sheet_name
        
        prompt_jobs = excel_mgr.read_jobs()

        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                cfg.user_data_dir,
                headless=cfg.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )

            # 첫 페이지 준비
            page0 = browser.pages[0] if browser.pages else await browser.new_page()
            await page0.goto(cfg.chatgpt_url, wait_until="load")
            
            # 로그인 처리(첫 1회만)
            if login_success == False:
                await chatgpt_login(page0, cfg.USER_ID, cfg.USER_PW)
                login_success = True
                
            # 로그인 후 다시 메인 페이지
            await page0.goto(cfg.chatgpt_url, wait_until="load")

            # 나머지 탭 생성
            pages: List[Page] = [page0]
            for _ in range(cfg.num_tabs - 1):
                new_page = await browser.new_page()
                await new_page.goto(cfg.chatgpt_url, wait_until="load")
                pages.append(new_page)

            # ----- 작업 분배 (라운드 로빈) -----
            worker_jobs: List[List[Tuple[int, str]]] = [[] for _ in range(cfg.num_tabs)]
            for i, job in enumerate(prompt_jobs):
                worker_index = i % cfg.num_tabs
                worker_jobs[worker_index].append(job)
                
            # ----- 워커 세션 생성 & 병렬 실행 -----
            tasks = []
            for idx, jobs in enumerate(worker_jobs):
                if not jobs: continue
                session = ChatGPTSession(pages[idx], cfg, worker_id=idx)
                tasks.append(asyncio.create_task(worker_job(session, jobs)))

            all_results_nested: List[List[Tuple[int, str]]] = await asyncio.gather(*tasks)

            # 결과 flatten
            all_results: List[Tuple[int, str]] = [
                item for worker_res in all_results_nested for item in worker_res
            ]

            # ----- 결과를 엑셀에 반영 후 저장 -----
            excel_mgr.apply_results(all_results)
            excel_mgr.save()

            log(f"\n모든 작업 완료. 결과가 '{cfg.excel_path}'에 저장되었습니다.")

            # await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
