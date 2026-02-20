from dataclasses import dataclass

from playwright.sync_api import sync_playwright

from logger_provider import configure_logging

MAX_AUTH_DEFAULT_NAV_TIMEOUT = 60000  # miliseconds


@dataclass
class AuthConfig:
    AUTH_FILE_NAME: str
    AUTH_USERNAME: str
    AUTH_PASSWORD: str
    AUTH_LINK: str
    AUTH_MAX_DEFAULT_NAVIGATION_TIMEOUT: int
    AUTH_USERNAME_LOCATOR: str
    AUTH_SUBMIT_USERNAME_BUTTON_LOCATOR: str
    AUTH_PASSWORD_LOCATOR: str
    AUTH_SUBMIT_PASSWORD_BUTTON_LOCATOR: str


class AuthProvider:
    """
    Provider class used to create an authentication session using the username and password provided in the constructor.


    Stores the auth session information in the path provided in ``auth_file_name`` after ``AuthProvider.create_authentication_context_session()`` is called.
    """

    def __init__(self, username: str, password: str, auth_file_name: str) -> None:
        base_link = "https://datalink.miovision.com/"
        auth_username_locator = 'input[name="username"]'

        auth_username_submit_button_locator = 'button[type="submit"]'
        auth_password_locator = 'input[name="password"]'
        auth_password_submit_button_locator = 'button[type="submit"]'

        self.auth_config = AuthConfig(
            AUTH_FILE_NAME=auth_file_name,
            AUTH_USERNAME=username,
            AUTH_PASSWORD=password,
            AUTH_LINK=base_link,
            AUTH_MAX_DEFAULT_NAVIGATION_TIMEOUT=MAX_AUTH_DEFAULT_NAV_TIMEOUT,
            AUTH_USERNAME_LOCATOR=auth_username_locator,
            AUTH_SUBMIT_USERNAME_BUTTON_LOCATOR=auth_username_submit_button_locator,
            AUTH_PASSWORD_LOCATOR=auth_password_locator,
            AUTH_SUBMIT_PASSWORD_BUTTON_LOCATOR=auth_password_submit_button_locator,
        )

        self.logger = configure_logging(logger_name="AuthProvider")

    def create_authentication_context_session(self) -> str:
        """
        Automate authentication and store session state in the auth file name address provided. Return the path
        of the file name with the auth session stored.
        """

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context()
            context.set_default_navigation_timeout(
                self.auth_config.AUTH_MAX_DEFAULT_NAVIGATION_TIMEOUT
            )
            page = context.new_page()

            self.logger.info(
                "[create_auth_credentials]: Started navigation to auth link"
            )
            page.goto(self.auth_config.AUTH_LINK)

            # Input and submit username
            self.logger.info(
                "[create_auth_credentials]: Started completion of username"
            )
            page.locator(self.auth_config.AUTH_USERNAME_LOCATOR).type(
                self.auth_config.AUTH_USERNAME
            )
            page.locator(
                self.auth_config.AUTH_SUBMIT_USERNAME_BUTTON_LOCATOR
            ).first.click()

            # Input and submit password
            self.logger.info(
                "[create_auth_credentials]: Started completion of password"
            )
            page.locator(self.auth_config.AUTH_PASSWORD_LOCATOR).type(
                self.auth_config.AUTH_PASSWORD
            )
            page.locator(
                self.auth_config.AUTH_SUBMIT_PASSWORD_BUTTON_LOCATOR
            ).first.click()

            # Wait for page load
            self.logger.info("[create_auth_credentials]: Waiting for load state")
            page.wait_for_load_state()

            # Saving auth details
            self.logger.info("[create_auth_credentials]: Saved auth details")
            context.storage_state(path=self.auth_config.AUTH_FILE_NAME)

            # Clean up
            self.logger.info(
                "[create_auth_credentials]: Closing page, context, and browser"
            )
            page.close()
            context.close()
            browser.close()

        return self.auth_config.AUTH_FILE_NAME
