import sys
from collections import defaultdict
from datetime import datetime
from logging import getLogger
from pathlib import Path
from time import sleep
from typing import Dict, List

import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

logger = getLogger(__name__)


class SubmittedCodesDownloader:
    """AtCoder submitted codes downloader"""

    def __init__(
        self,
        atcoder_user_id: str,
        output_dir: str = "./submitted",
        first_submit_year: int = 2016,
    ):
        self.atcoder_user_id = atcoder_user_id
        self.first_epoch_second = int(datetime(first_submit_year, 1, 1).timestamp())
        self.output_dir = output_dir

        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        chrome_service = webdriver.chrome.service.Service(
            executable_path=ChromeDriverManager().install()
        )
        self.driver = webdriver.Chrome(service=chrome_service, options=options)

        self.problem_id_to_number_dict = self._init_long_contest_number_dict()

    def _init_long_contest_number_dict(self):
        """init problem_id_to_number_dict for contests which has many problems
        - https://atcoder.jp/contests/typical90
        - https://atcoder.jp/contests/APG4b
        """
        NUM_ALPHABETS = 26
        MAX_PROBLEM_PER_CONTEST = 201
        problem_id_to_number_dict = {}
        for i in range(MAX_PROBLEM_PER_CONTEST):
            first_chr = chr(i // NUM_ALPHABETS + ord("a") - 1)
            second_chr = chr(i % NUM_ALPHABETS + ord("a"))
            if first_chr == "`":
                first_chr = ""
            problem_id_to_number_dict[first_chr + second_chr] = f"{i + 1}".zfill(3)
        return problem_id_to_number_dict

    def get_submissions_info(self):
        """Get Atcoder submissions information using https://kenkoooo.com/atcoder/atcoder-api

        Returns:
            submissions_info (Dict): Atcoder submissions information
        """

        submissions_info = []
        start_epoch_second = self.first_epoch_second

        # Submission API returns up to 500 pieces of info in a single request.
        # https://github.com/kenkoooo/AtCoderProblems/blob/master/doc/api.md#user-submissions
        cnt_info = 500
        while cnt_info >= 500:
            try:
                api_url = (
                    "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user="
                    + f"{self.atcoder_user_id}&from_second={start_epoch_second}"
                )
                response = requests.get(api_url)
                tmp_submissions_info: List = response.json()
                cnt_info = len(tmp_submissions_info)
                tmp_submissions_info = sorted(
                    tmp_submissions_info, key=lambda x: x["id"]
                )  # As a result, info is sorted by the time it was submitted.
                start_epoch_second = tmp_submissions_info[-1]["epoch_second"] + 1
                submissions_info = submissions_info + tmp_submissions_info

            except requests.exceptions.RequestException as e:
                logger.error(e)

            # "Please sleep for more than 1 second between accesses."
            # https://github.com/kenkoooo/AtCoderProblems/blob/master/doc/api.md#caution
            sleep(2)

        return submissions_info

    def _organize_submissions_info_by_contest(self, submissions_info: List) -> Dict:
        """Organize the Submission API return value by contest.

        Args:
            submissions_info (List): Submission API return value

        Returns:
            info_by_contest (Dict): Submission Info which is organized by contest
        """

        info_by_problem = {}
        for (
            submission_info
        ) in submissions_info:  # Overwrite with latest submission results
            if submission_info["result"] != "AC":
                continue
            info_by_problem[submission_info["problem_id"]] = submission_info

        info_by_contest: Dict = defaultdict(list)
        for submission_info in info_by_problem.values():
            info_by_contest[submission_info["contest_id"]].append(submission_info)

        return info_by_contest

    def _get_output_file_path(self, submission_info_by_problem: Dict) -> Path:
        problem_id = submission_info_by_problem["problem_id"]
        file_name = problem_id.split("_")[-1]

        # change file name for typical90 contest
        if submission_info_by_problem["contest_id"] == "typical90":
            file_name = self.problem_id_to_number_dict[file_name]

        used_lang = submission_info_by_problem["language"]
        file_extension = ""
        if "Py" in used_lang:
            file_extension = "py"
        elif "Rust" in used_lang:
            file_extension = "rs"
        elif "C++" in used_lang:
            file_extension = "cpp"

        output_path = Path(
            f"{self.output_dir}/{submission_info_by_problem['contest_id']}/{file_name}.{file_extension}"
        )
        return output_path

    def _get_submitted_code(self, code_url: str):
        try:
            self.driver.get(code_url)
            wait = WebDriverWait(self.driver, 20)
            wait.until(EC.presence_of_element_located((By.ID, "submission-code")))
            code = self.driver.find_element(by=By.ID, value="submission-code")
            code_text = code.get_attribute("innerText").replace(
                " \n", "\n"
            )  # remove not written space

        except TimeoutException as e:
            logger.error(e)

        return code_text

    def _get_submission_url(self, problem_submission_info):
        return (
            f"https://atcoder.jp/contests/{problem_submission_info['contest_id']}/"
            + f"submissions/{str(problem_submission_info['id'])}"
        )

    def exec_download(
        self,
        overwrite: bool = False,
    ):
        """exec donwload

        Args:
            overwrite (bool, optional): Overwrite local saved data or not. Defaults to False.
        """
        submissions_info = self.get_submissions_info()
        submissions_info_by_contest = self._organize_submissions_info_by_contest(
            submissions_info
        )

        for (
            contest_name,
            contest_submission_info,
        ) in submissions_info_by_contest.items():
            Path(f"{self.output_dir}/{contest_name}").mkdir(exist_ok=True, parents=True)

            for problem_submission_info in contest_submission_info:
                output_file_path = self._get_output_file_path(problem_submission_info)
                if output_file_path.exists() and not overwrite:
                    continue

                submission_url = self._get_submission_url(problem_submission_info)

                code_text = self._get_submitted_code(submission_url)
                with open(output_file_path, "w") as f:
                    f.write(code_text)

                sleep(2)

        self.driver.quit()


if __name__ == "__main__":
    """
    sys.argv[1] (str): AtCoder User name
    sys.argv[2] (str): Output Dirctory Path
    sys.argv[3] (int): First Submit Year
    """
    logger.info("start!")
    downloder = SubmittedCodesDownloader(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    downloder.exec_download()
    logger.info("finish!")
