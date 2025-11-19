import os
from dataclasses import dataclass


@dataclass
class Config:
    # Excel
    DATA_DIR = "data"
    # FILE_NAME = "gpt_prompt_queries_data.xlsx"
    FILE_NAME = "달바 콘텐츠 시딩.xlsx"
    excel_path: str = os.path.join(os.getcwd(), DATA_DIR, FILE_NAME)
    prompt_col: str = "B"
    start_col_row: int = 1
    start_row: int = 2

    # ChatGPT
    chatgpt_url: str = "https://chatgpt.com/"
    user_data_dir: str = "user_data_chatgpt"
    headless: bool = False
    __USER_ID = "tlsdnd001@naver.com"
    __USER_PW = "qlqjqlqj8520"
    
    @property
    def USER_ID(self):
        return self.__USER_ID
    
    @property
    def USER_PW(self):
        return self.__USER_PW

    # 병렬 처리
    num_tabs: int = 10

    # 타임아웃 및 딜레이
    queries_wait_timeout: float = 35.0
    reload_wait_timeout: float = 20.0
    max_reload_try: int = 3
    min_answer_wait: float = 3.0
    between_prompts_sleep: float = 1.0