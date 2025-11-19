import os
from dataclasses import dataclass


@dataclass
class Config:
    # Excel
    DATA_DIR = "Data"
    FILE_NAME = "Contents_Seeding.xlsx"
    excel_path: str = os.path.join(os.getcwd(), DATA_DIR, FILE_NAME)
    prompt_col: str = "B"
    start_col_row: int = 1
    start_row: int = 2

    # ChatGPT
    __USER_ID = "tlsdnd001@naver.com"
    __USER_PW = "qlqjqlqj8520"
    chatgpt_url: str = "https://chatgpt.com/"
    check_json_url: str = "https://chatgpt.com/backend-api/conversation/"
    user_data_dir: str = "user_data_chatgpt"
    headless: bool = False
    
    # 병렬 처리
    num_tabs: int = 10

    # 타임아웃 및 딜레이
    queries_wait_timeout: float = 5.0
    reload_wait_timeout: float = 10.0
    max_reload_try: int = 3
    min_answer_wait: float = 3.0
    between_prompts_sleep: float = 1.0

    @property
    def USER_ID(self):
        return self.__USER_ID
    
    @property
    def USER_PW(self):
        return self.__USER_PW