from logging import getLogger
from pathlib import Path

import pytest
from src.atcoder.submitted_codes_downloader import SubmittedCodesDownloader

logger = getLogger(__name__)


@pytest.mark.github_actions
def test_init_long_contest_number_dict():
    downloder = SubmittedCodesDownloader("USERNAME", "OUTPUT_DIR", 2021)

    assert downloder.problem_id_to_number_dict["a"] == "001"
    assert downloder.problem_id_to_number_dict["z"] == "026"
    assert downloder.problem_id_to_number_dict["aa"] == "027"
    assert downloder.problem_id_to_number_dict["az"] == "052"


get_output_file_path_data_list = [
    (
        {
            "contest_id": "sample_contest",
            "problem_id": "sample_sample_x",
            "language": "Python(3.X.X)",
        },
        Path("OUTPUT_DIR/sample_contest/x.py"),
    ),
    (
        {
            "contest_id": "sample_contest",
            "problem_id": "sample_sample_x",
            "language": "Rust(1.X.X)",
        },
        Path("OUTPUT_DIR/sample_contest/x.rs"),
    ),
    (
        {
            "contest_id": "sample_contest",
            "problem_id": "sample_sample_x",
            "language": "C++XXX",
        },
        Path("OUTPUT_DIR/sample_contest/x.cpp"),
    ),
]


@pytest.mark.github_actions
@pytest.mark.parametrize(
    "submission_info_by_problem, expect_path", get_output_file_path_data_list
)
def test_get_output_file_path(submission_info_by_problem, expect_path):
    downloder = SubmittedCodesDownloader("USERNAME", "OUTPUT_DIR", 2021)
    output_path = downloder._get_output_file_path(submission_info_by_problem)

    assert output_path == expect_path


@pytest.mark.github_actions
def test_get_submission_url():
    downloder = SubmittedCodesDownloader("USERNAME", "OUTPUT_DIR", 2021)
    submission_info_by_problem = {
        "contest_id": "sample_contest",
        "problem_id": "sample_sample_x",
        "id": "1234567890",
    }

    submission_url = downloder._get_submission_url(submission_info_by_problem)
    ans_submission_url = (
        "https://atcoder.jp/contests/sample_contest/submissions/1234567890"
    )

    assert submission_url == ans_submission_url
