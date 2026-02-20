import datetime
import logging
import re
from dataclasses import dataclass

from playwright.sync_api import Page, sync_playwright

from logger_provider import configure_logging

MAX_MIOVISION_ID_MAX_DEFAULT_NAVIGATION_TIMEOUT = 90000  # milliseconds


@dataclass
class MiovisionInfoProviderProviderConfig:
    AUTH_CONTEXT_FILE_NAME: str
    BASE_LINK: str
    START_YEAR: int
    END_YEAR: int
    MIOVISION_ID_LOCATOR: str
    MIOVISION_TOTAL_COUNT_VALIDTION_LOCATOR: str
    MIOVISION_ID_MAX_DEFAULT_NAVIGATION_TIMEOUT: int


class MiovisionInfoProvider:
    """
    Provider used to automate the scraping of miovision study types and ids for further downstream tasks using the provided
    ``auth_context_file_name`` and, start and end year.
    """

    def __init__(
        self, auth_context_file_name: str, start_year: int, end_year: int
    ) -> None:
        base_link = "https://datalink.miovision.com/"
        miovision_id_locator = 'tr[class="marker_hover"] >> div.miogrey'
        miovision_validation_locator = "div.text-center"

        self.id_context: dict[str, str] = {}

        self.logger = configure_logging(logger_name="URLsProvider")
        self.config = MiovisionInfoProviderProviderConfig(
            AUTH_CONTEXT_FILE_NAME=auth_context_file_name,
            BASE_LINK=base_link,
            START_YEAR=start_year,
            END_YEAR=end_year,
            MIOVISION_ID_LOCATOR=miovision_id_locator,
            MIOVISION_ID_MAX_DEFAULT_NAVIGATION_TIMEOUT=MAX_MIOVISION_ID_MAX_DEFAULT_NAVIGATION_TIMEOUT,
            MIOVISION_TOTAL_COUNT_VALIDTION_LOCATOR=miovision_validation_locator,
        )

    def check_date_pattern(self, date_string: str) -> bool:
        """
        Check if the date matches YYYY-MM-DD
        ### Parameters
        1. date_string : ``str``
            - String to be compared against the format

        ### Returns
        True or False for a valid or invalid pattern, respectively.
        """
        try:
            datetime.datetime.strptime(date_string, "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def retrieve_study_type_id(
        self,
        page: Page,
        logger: logging.Logger,
        start_date: str,
        end_date: str,
        base_url: str,
        id_locator: str,
        validation_locator,
    ) -> list[tuple[str, str]]:
        """
        Given the page, navigate to the base url after adding the start date and end date and return all miovsion ID's and Study Types from the page
        in the form ``(<Study Type>,<ID>)``

        ### Parameters
        1. page: ``Page``
            - Page object used for navigation
        2. logger: ``logging.Logger``
            - Used for logging purposes
        3. start_date: ``str``
            - Start date should be provided in 'YYYY-MM-DD'
        4. end_date : ``str``
            - End date should be provided in 'YYYY-MM-DD'
        5. base_url : ``str``
            - Base url upon which the navigation url is built
        6. id_locator : ``str``
            - Element css used to locate the space where the IDs are stored.
        7. validtion_locator : ``str``
            - Element css used to locaate the number of studies per page to validate that each one was extracted

        ### Returns
        List of study types and ID's
        """
        if not self.check_date_pattern(start_date) or not self.check_date_pattern(
            end_date
        ):
            raise Exception("Dates muste be given in YYYY-MM-DD format")

        link = (
            base_url
            + f"studies/?end_date={end_date}&start_date={start_date}&state=Published"
        )

        logger.info(f"[retrieve_ids] Navigating to {link}")
        page.goto(link)

        miovision_total_studies_count_text: str = page.locator(
            validation_locator
        ).inner_text()
        miovision_total_studies_count: int = int(
            miovision_total_studies_count_text.split("Studies")[0]
        )  # Text is in the form: "<Count> Studies"

        uncleaned_ids = page.locator(id_locator).all_inner_texts()
        cleaned_study_types_ids = list()

        # The ID and study study come after any occurences of m or h, e.g. "24 h 30 m ATR#1226458 "
        # Here ATR is the study type and 1226458 is the study ID
        match_pattern = "[mh]"
        for id_text in uncleaned_ids:
            study_type_id_text = re.split(match_pattern, id_text)[-1]
            clean_id = study_type_id_text.split("#")[-1].strip()
            clean_study_type = study_type_id_text.split("#")[0].strip()

            cleaned_study_types_ids.append((clean_study_type, clean_id))

        assert len(cleaned_study_types_ids) == miovision_total_studies_count, (
            f"Mismatch between extracted studies ({len(cleaned_study_types_ids)}) and expected number of studies ({miovision_total_studies_count})."
        )
        logger.info(
            f"[retrieve_ids] Returning {len(cleaned_study_types_ids)} ids, expected {miovision_total_studies_count}."
        )
        return cleaned_study_types_ids

    def get_miovision_study_types_ids(self) -> list[tuple[str, str]]:
        """
        Return list of scraped urls pointing to miovision studies for the provided time span such that each
        element is in the form ``(<Study Type>,<ID>)``
        """
        with sync_playwright() as playwright:
            start_year = self.config.START_YEAR
            end_year = self.config.END_YEAR

            miovision_study_types_ids: list[tuple[str, str]] = list()

            self.logger.info("[scrape_miovision_ids] Starting browser")
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                storage_state=self.config.AUTH_CONTEXT_FILE_NAME
            )
            context.set_default_navigation_timeout(
                self.config.MIOVISION_ID_MAX_DEFAULT_NAVIGATION_TIMEOUT
            )
            page = context.new_page()
            while start_year <= end_year:
                for i in range(1, 13):
                    start_date = f"{start_year}-{i}-01"
                    if i == 12:
                        end_date = f"{start_year + 1}-01-01"
                    else:
                        end_date = f"{start_year}-{i + 1}-01"

                    self.logger.info(
                        f"[scrape_miovision_ids] Getting ids from {start_date} to {end_date}"
                    )
                    try:
                        monthly_study_types_ids = self.retrieve_study_type_id(
                            page=page,
                            logger=self.logger,
                            start_date=start_date,
                            end_date=end_date,
                            base_url=self.config.BASE_LINK,
                            id_locator=self.config.MIOVISION_ID_LOCATOR,
                            validation_locator=self.config.MIOVISION_TOTAL_COUNT_VALIDTION_LOCATOR,
                        )

                        monthly_unique_ids = set(
                            [id for study_type, id in monthly_study_types_ids]
                        )

                        if len(monthly_unique_ids) != len(monthly_study_types_ids):
                            raise ValueError(
                                f"Duplicate ID's found within range {start_date} - {end_date}"
                            )

                        miovision_study_types_ids.extend(monthly_study_types_ids)

                    except ValueError as e:
                        self.logger.error(f"[scrape_miovision_ids] Error: {e}")

                start_year += 1

            self.logger.info(
                "[scrape_miovision_ids] Closing page, context, and browser"
            )
            page.close()
            context.close()
            browser.close()
            return miovision_study_types_ids
