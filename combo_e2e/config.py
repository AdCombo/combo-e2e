from combo_e2e.helpers.base_config import BaseConfig


class Config(BaseConfig):
    """
    e2e tests config. allowed types for attributes and nested dictionaries:
    [str, int, float, Decimal, bool]. Exception will bw thrown while trying to use any other type.
    ----------------
    Config update from environment variables is supported. UPDATE_FROM_ENV needs to be set to True and
    ENV_KEY_PREFIX needs to contain prefix for environment variables. Nested attributes are separated
    with `__`. Example:
    If ENV_KEY_PREFIX = 'combo_e2e', then to override Config.BASE_APP_CONFIG['test_app]['base_url']
    environment variable 'combo_e2e__BASE_APP_CONFIG__test_app__base_url' is needed.
    """

    UPDATE_FROM_ENV = True
    ENV_KEY_PREFIX = "test"

    # base configurations for applications
    # Something like this
    # 'test_app': {
    #     'base_url': 'http://application_url.com',
    #     'page_loader_css_class': 'pageLoaderClass',
    #     'table_loader_css_class': 'tableLoaderClass',
    #     'modal_visible_css_class': 'custom modal class',
    #     'has_page_ready_script': True,  # need to check window.e2e_ready attribute
    # },
    BASE_APP_CONFIG = {}

    # selenium config
    WEB_DRIVER_WAIT = 60
    WEB_DRIVER_LOG_LEVEL = "warning"
    # path to save screenshots to in case of errors
    SCREENSHOT_PATH = "/tmp/selenium_screenshots"
    ENABLE_CONSOLE_LOG = True
    CONSOLE_LOG_PATH = "/tmp/selenium_console_logs"

    # chrome driver downloader config (https://chromedriver.chromium.org/)
    CHROME_DRIVER_URL = "https://chromedriver.storage.googleapis.com/"
    CHROME_DRIVER_VER = "LATEST_RELEASE"
    # Major versions of chrome and chrome driver must match
    # If you encounter an error: This version of ChromeDriver only supports Chrome version XXX
    # then you need to get correct version from https://chromedriver.chromium.org/downloads and enter below
    DEFAULT_DRIVER_VER = "108.0.5359.71"
    # system type to download driver for
    CHROME_DRIVER_FILE_NAME = "chromedriver_linux64.zip"
    # if empty string, then the default path in tmp is used
    CHROME_DRIVER_PATH = ""
    # re download driver every time tests are run
    RELOAD_DRIVER = False
    # kill driver after tests (in case of False browser won't close)
    KILL_DRIVER = True
    # changes selenium default load timeout
    DRIVER_PAGE_LOAD_TIMEOUT = 20
    CHROME_DRIVER_LOG_PATH = ""
    CHROME_DRIVER_VERBOSE = False

    # chrome config
    # headless_mode (set to true while using in environment without graphic shell)
    CHROME_HEADLESS_MODE = True
    # chrome options (parameter separator - ";")
    CHROME_OPTIONS = "window-size=1920,1080;"
    CHROME_DOWNLOADS_PATH = "/tmp/chrome_downloads"

    DATA_E2E_ATTRIBUTE = "data-e2e"
    TABLE_E2E_ATTRIBUTE = "data-e2e-table"
    DEFAULT_TABLE_TAG = "p-table"
    NESTED_TABLE_TAG = "table"


config = Config()
