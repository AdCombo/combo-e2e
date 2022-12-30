import logging
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.remote.remote_connection import LOGGER
from selenium.webdriver.remote.webdriver import WebDriver

from combo_e2e.config import config
from combo_e2e.helpers.chromedriver_loader import ChromeDriverLoader


def set_log_level_from_config():
    log_level = config.WEB_DRIVER_LOG_LEVEL
    log_level = getattr(logging, log_level.upper(), logging.WARNING)
    LOGGER.setLevel(log_level)


class E2EDriver:
    downloads_dir: Optional[Path] = None

    @classmethod
    def _get_selenium_service(cls) -> Service:
        if not hasattr(cls, "__selenium_service"):
            path = ChromeDriverLoader.driver_path
            if not path:
                raise AttributeError("Get empty driver path.")
            service = Service(path)
            service.start()
            setattr(cls, "__selenium_service", service)
        return getattr(cls, "__selenium_service")

    @classmethod
    def _create(cls) -> WebDriver:
        set_log_level_from_config()
        kwargs = {}
        serv = cls._get_selenium_service()
        caps = cls._make_desired_capabilities()
        options = cls._make_chrome_options()
        if options.arguments:
            kwargs["options"] = options
        driver: WebDriver = webdriver.Remote(
            serv.service_url, desired_capabilities=caps, **kwargs
        )
        if config.DRIVER_PAGE_LOAD_TIMEOUT:
            driver.set_page_load_timeout(config.DRIVER_PAGE_LOAD_TIMEOUT)
        return driver

    @classmethod
    def _make_chrome_options(cls) -> Options:
        options = Options()
        if config.CHROME_HEADLESS_MODE:
            options.add_argument("--headless")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
        if config.CHROME_OPTIONS:
            parts = filter(lambda o: o.strip(), config.CHROME_OPTIONS.split(";"))
            for opt in parts:
                options.add_argument(opt)
        if config.CHROME_DOWNLOADS_PATH:
            options = cls._make_options_for_downloads(options)
        return options

    @classmethod
    def _make_dir_for_downloads(cls) -> Path:
        downloads_path = Path(config.CHROME_DOWNLOADS_PATH)
        if not downloads_path.exists():
            downloads_path.mkdir(parents=True)
        return downloads_path

    @classmethod
    def _make_options_for_downloads(cls, options: Options):
        cls.downloads_dir = cls._make_dir_for_downloads()
        prefs = {
            "browser.download.manager.showWhenStartingbrowser.download.manager.showWhenStarting": False,
            "download.default_directory": str(cls.downloads_dir),
            "download.directory_upgrade": True,
            "download.prompt_for_download": False,
            "browser.set_download_behavior": {"behavior": "allow"},
        }
        options.add_experimental_option("prefs", prefs)
        options.add_experimental_option("useAutomationExtension", False)
        return options

    @classmethod
    def _make_desired_capabilities(cls) -> DesiredCapabilities:
        caps = DesiredCapabilities.CHROME
        chrome_options = Options()
        chrome_options.add_argument("disable-gpu")
        if not config.CHROME_HEADLESS_MODE:
            chrome_options.add_argument("start-maximized")

        caps.update(chrome_options.to_capabilities().copy())
        if config.ENABLE_CONSOLE_LOG:
            caps["goog:loggingPrefs"] = {"browser": "ALL"}
        return caps

    @classmethod
    def _destroy(cls) -> None:
        driver = getattr(cls, "__cached_driver", None)
        if driver and driver.session_id:
            driver.quit()
            driver.session_id = None
            delattr(cls, "__cached_driver")
            cls.downloads_dir = None

    @classmethod
    def get_driver(cls, fresh_session: bool = False) -> WebDriver:
        if fresh_session:
            cls._destroy()

        if not hasattr(cls, "__cached_driver"):
            setattr(cls, "__cached_driver", cls._create())

        return getattr(cls, "__cached_driver")

    @classmethod
    def quit(cls) -> None:
        cls._destroy()
