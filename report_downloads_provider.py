import json
from dataclasses import dataclass, field
from logging import Logger
from pathlib import Path
from typing import Protocol, TypedDict

import requests

from existing_file_validation import ExistingFileValidator


@dataclass
class DataDownloadConfig:
    study_id: str
    study_type: str
    file_name: Path
    time_interval: str
    time_interval_seconds: int = field(default=0)

    def __post_init__(self):
        time_interval_mapping = {
            "1 minute": 60,
            "5 minutes": 300,
            "10 minutes": 600,
            "30 minutes": 1800,
            "1 hour": 3600,
        }
        if self.time_interval not in time_interval_mapping:
            raise ValueError(
                f"time_interval must be one of {list(time_interval_mapping.keys())}"
            )
        self.time_interval_seconds = time_interval_mapping[self.time_interval]


class CookieType(TypedDict):
    name: str
    value: str
    domain: str
    path: str
    expires: int
    httpOnly: bool
    secure: bool
    sameSite: str


# Interfaces
class ContentDownloader(Protocol):
    def download_content(self, id: str, time_interval: str) -> bytes: ...


class ContentSaver(Protocol):
    def save_content(self, content: bytes) -> None: ...


class HeadersProvider(Protocol):
    def get_headers(
        self,
    ) -> dict: ...


class SessionAuthProvider(Protocol):
    def get_token_value(self, token_name: str) -> str: ...


# Implementations
class JSONSessionAuthProvider:
    def __init__(self, json_file_name: str) -> None:
        try:
            with open(json_file_name) as file:
                self.session_json = json.loads(file.read())
        except Exception as e:
            raise e

    def get_token_value(self, token_name: str) -> str:
        cookies_list: list[CookieType] = self.session_json["cookies"]

        for cookie in cookies_list:
            if cookie["name"] == token_name:
                return cookie["value"]

        return "Token value for provided token_name not found"


class MiovisionHeadersProvider:
    def __init__(self, session_auth_provider: SessionAuthProvider) -> None:
        self.auth_provider = session_auth_provider
        self.token_name = "central_production_session_id"

    def get_headers(self) -> dict:
        self.token_value = self.auth_provider.get_token_value(self.token_name)

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "cookie": f"central_production_session_id={self.token_value}; return_to=https://datalink.miovision.com/studies?end_date=2023-09-30&start_date=2023-09-01; intercom-device-id-mi3ti0da=3fd9cefa-c2a6-4b36-8774-30be6acd47a0; intercom-session-mi3ti0da=TXBVR3lWTmErNFRtWWFhTEZSYy93SGJacVNFMVlIaVJiR2ZtblRadWxyYXF5NC9RSXc4UThCS3lYVnQ1SnVHLy0tRmg5UFhvWExvbVV2ejhjVGJtMndXZz09--c5a252b23a20dd34264913de39638c846f16f6e8; download_token_1727916324=1727916324",
            "Referer": "https://datalink.miovision.com/studies/1127843",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

        return headers


class APIContentDownloader:
    def __init__(self, headers_provider: HeadersProvider) -> None:
        self.headers_provider = headers_provider

    def download_content(self, id: str, time_interval: str) -> bytes:
        api_endpoint = f"https://datalink.miovision.com/studies/{id}/report?download_token=1727917620&report%5Bformat%5D=xlsx&report%5Bbin_size%5D={time_interval}&report%5Bworksheet_grouping%5D=by_direction&report%5Bapproach_order%5D=n_ne_e_se_s_sw_w_nw&report%5Binclude_raw_data%5D=false&report%5Bforced_peak_enabled%5D=false"

        try:
            response = requests.get(
                url=api_endpoint, headers=self.headers_provider.get_headers()
            )
        except Exception as e:
            return f"Error: {e}".encode()
        return response.content


class ExcelFileContentSaver:
    def __init__(self, file_name: Path) -> None:
        self.file_name = file_name

    def save_content(self, content: bytes) -> None:
        try:
            with open(self.file_name, mode="wb") as file:
                file.write(content)
        except Exception as e:
            raise e


class DownloadsProvider:
    """
    Downloads the excel reports for the following studies with the requested time granularity.
    Expects the list passed in to be contain ``(<Study Type : str>,<Study ID : str>)`` for each element.
    """

    def __init__(
        self,
        content_downloader: ContentDownloader,
        logger: Logger,
        content_saver: ContentSaver,
        download_config: DataDownloadConfig,
    ) -> None:
        self.content_provider = content_downloader
        self.content_saver = content_saver
        self.study_id = download_config.study_id
        self.time_interval = download_config.time_interval_seconds
        self.logger = logger

    def download_file(self) -> None:
        content = self.content_provider.download_content(
            id=self.study_id, time_interval=str(self.time_interval)
        )
        self.content_saver.save_content(content=content)
        self.logger.info(f"Downloaded report for {self.study_id}")


class ValidatingDownloader:
    def __init__(
        self,
        base_downloader: DownloadsProvider,
        existing_file: ExistingFileValidator,
        file_path: Path,
    ) -> None:
        self.existing_file_validator = existing_file
        self.base_downloader = base_downloader
        self.file_path = file_path

    def download_file(self) -> None:
        download_count = 0
        while not self.existing_file_validator.is_existing_file(self.file_path):
            download_count += 1
            self.base_downloader.download_file()
