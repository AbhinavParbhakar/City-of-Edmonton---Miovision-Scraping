import argparse
import os
from dataclasses import dataclass
from multiprocessing.pool import Pool
from pathlib import Path

import dotenv

from auth_provider import AuthProvider
from existing_file_validation import LocalStorageExistingFileValidator
from logger_provider import configure_logging
from miovision_info_provider import MiovisionInfoProvider
from report_downloads_provider import (
    APIContentDownloader,
    DataDownloadConfig,
    DownloadsProvider,
    ExcelFileContentSaver,
    JSONSessionAuthProvider,
    MiovisionHeadersProvider,
    ValidatingDownloader,
)


@dataclass
class CommandLineArguments:
    miovision_username: str
    miovision_password: str
    auth_session_file_path: str
    miovision_base_folder: str
    start_year: str
    end_year: str
    time_interval: str

    def __post_init__(self):
        if not self.start_year.isdigit() or not self.end_year.isdigit():
            raise ValueError("Start Year and End Year must both digits")

        if int(self.end_year) < int(self.start_year):
            raise ValueError("Start year must be before end year")

        if ".json" not in self.auth_session_file_path:
            raise ValueError(
                "auth_session_file_path must be in the following format '[path].json'"
            )


def download_file(downloads: ValidatingDownloader):
    downloads.download_file()


def configure_parser(arguments: list[str]) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="Miovision Scraper",
        description="Downloads all Miovision studies in the specified time range",
    )

    for arg in arguments:
        parser.add_argument(arg)
    return parser


if __name__ == "__main__":
    arguments = [
        "auth_session_file_path",
        "miovision_base_folder",
        "start_year",
        "end_year",
        "time_interval",
    ]

    dotenv.load_dotenv()
    username = os.environ["MIOVISION_USERNAME"]
    password = os.environ["MIOVISION_PASSWORD"]

    if not username or not password:
        raise Exception(
            "Username and Password must be specified in the .env placed in the root of directory"
        )

    parser = configure_parser(arguments)
    args: dict[str, str] = vars(parser.parse_args())

    arguments = CommandLineArguments(
        miovision_username=username,
        miovision_password=password,
        auth_session_file_path=args["auth_session_file_path"],
        miovision_base_folder=args["miovision_base_folder"],
        start_year=args["start_year"],
        end_year=args["end_year"],
        time_interval=args["time_interval"],
    )

    if not os.path.exists(arguments.miovision_base_folder):
        os.mkdir(arguments.miovision_base_folder)

    auth = AuthProvider(
        username=arguments.miovision_username,
        password=arguments.miovision_password,
        auth_file_name=arguments.auth_session_file_path,
    )

    miovision_info = MiovisionInfoProvider(
        auth_context_file_name=arguments.auth_session_file_path,
        start_year=int(arguments.start_year),
        end_year=int(arguments.end_year),
    )

    auth.create_authentication_context_session()
    distinct_ids: set[str] = set()
    miovision_info_list = miovision_info.get_miovision_study_types_ids()

    download_providers: list[ValidatingDownloader] = []

    for study_type, study_id in miovision_info_list:
        distinct_ids.update([study_id])
        data = DataDownloadConfig(
            study_id=study_id,
            study_type=study_type,
            file_name=Path(arguments.miovision_base_folder)
            / f"{study_type}-{study_id}.xlsx",
            time_interval=arguments.time_interval,
        )
        session_provider = JSONSessionAuthProvider(
            json_file_name=arguments.auth_session_file_path
        )
        headers_provider = MiovisionHeadersProvider(session_provider)
        content_downloader = APIContentDownloader(headers_provider)
        content_saver = ExcelFileContentSaver(file_name=data.file_name)
        existing_file_validator = LocalStorageExistingFileValidator(
            Path(arguments.miovision_base_folder)
        )

        download_providers.append(
            ValidatingDownloader(
                DownloadsProvider(
                    content_downloader=content_downloader,
                    logger=configure_logging("DownloadsProvider"),
                    content_saver=content_saver,
                    download_config=data,
                ),
                existing_file=existing_file_validator,
                file_path=data.file_name,
            )
        )
    cli_logger = configure_logging("CLI")
    cli_logger.info(f"Length of download providers: {download_providers.__len__()}")
    cli_logger.info(f"Distinct number of studies: {distinct_ids.__len__()}")
    with Pool(os.cpu_count()) as p:
        p.map(download_file, download_providers)
