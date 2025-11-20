import os
import platform

from dataclasses import dataclass


@dataclass
class Config:
    # System
    platform_info: str = platform.system()
    
    # Excel
    DATA_DIR = "Data"
    FILE_NAME = "Contents_Seeding.xlsx"
    excel_path: str = os.path.join(os.getcwd(), DATA_DIR, FILE_NAME)
    prompt_col: str = "B"
    start_col_row: int = 1
    start_row: int = 2
    result_check_start_col = 2  # B열부터 결과 체크

    # ChatGPT
    __user_id = "tlsdnd001@gmail.com"
    __user_pw = "dnddl6290!@"
    chatgpt_url: str = "https://chatgpt.com/"
    check_json_url: str = "https://chatgpt.com/backend-api/conversation/"
    user_data_dir: str = "user_data_chatgpt"
    headless: bool = False
    
    # 병렬 처리
    num_tabs: int = 1

    # 타임아웃 및 딜레이
    queries_wait_timeout: float = 10.0
    reload_wait_timeout: float = 10.0
    max_reload_try: int = 3
    min_answer_wait: float = 3.0
    between_prompts_sleep: float = 1.0
    
    @property
    def USER_ID(self):
        return self.__user_id
    
    @property
    def USER_PW(self):
        return self.__user_pw
    