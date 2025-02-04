import logging
import tempfile
import uuid
import zipfile
from pathlib import Path
from urllib.parse import urljoin

import pytest
import requests
from requests import Response, Timeout

from combo_e2e.config import config

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 20


class ChromeDriverLoaderException(Exception):
    pass


@pytest.mark.early
@pytest.fixture(scope="session", autouse=True)
def download_chromedriver(tmp_path_factory):
    """
    Fixture to be imported into conftest
    :param tmp_path_factory:
    :return:
    """
    tmp_path = Path(tempfile.gettempdir())
    if config.CHROME_DRIVER_PATH:
        driver_path = Path(config.CHROME_DRIVER_PATH)
        if not driver_path.exists():
            driver_path.mkdir(parents=True)
    else:
        driver_path = tmp_path.joinpath("chrome_driver")
    ChromeDriverLoader.download(tmp_path, driver_path)


class ChromeDriverLoader:
    """
    Class to download chromedriver
    """

    driver_name: str = "chromedriver"
    zip_driver_path: str = "chromedriver-{platform}"
    _path_to_store: Path = None
    path_to_download: Path = None
    driver_path: str = None
    version: str = ""

    @classmethod
    def download(cls, path_to_download: Path, driver_path: Path) -> None:
        logger.info("Prepare tests stage.")
        cls.path_to_download = path_to_download
        cls._path_to_store = driver_path

        if not config.RELOAD_DRIVER and cls.is_driver_exists():
            logger.info("Reloading driver disabled. Use exists chrome driver version")
            cls.driver_path = str(cls.make_driver_full_path())
            return

        logger.info(" Starting download chrome driver")
        version = cls._get_latest_version()
        archive_path = cls._download(version)
        cls.driver_path = cls._unzip(archive_path, version=version)
        logger.info(
            "Prepare tests stage. Chrome driver downloaded and saved in %s",
            cls.driver_path,
        )

    @classmethod
    def make_driver_full_path(cls) -> Path:
        return cls._path_to_store.joinpath(cls.driver_name)

    @classmethod
    def is_driver_exists(cls) -> bool:
        if cls.make_driver_full_path().exists():
            return True
        return False

    @classmethod
    def _get(cls, url: str) -> Response:
        try:
            res = requests.get(url, timeout=DEFAULT_TIMEOUT)
            if res.status_code == 200:
                return res
            else:
                raise ChromeDriverLoaderException(
                    f"Cannot download chromedriver. Url: {url}. "
                    f"Status_code: {res.status_code}"
                )
        except Timeout:
            raise ChromeDriverLoaderException(
                f"Cannot download chromedriver from {url}. Timeout error."
            )

    @classmethod
    def _get_latest_version(cls):
        version = config.DEFAULT_DRIVER_VER
        if not config.DEFAULT_DRIVER_VER:
            res = cls._get(config.CHROME_DRIVER_LAST_KNOWN_URL)
            try:
                versions = res.json()
                version = versions.get("channels", {}).get("Stable", {}).get("version")
            except Exception as e:
                raise ChromeDriverLoaderException(
                    f"Cannot get chromedriver version. Url: {config.CHROME_DRIVER_LAST_KNOWN_URL}. "
                    f"Response: {res.text}"
                )
        return version

    @classmethod
    def _is_old_version(cls, version: str) -> bool:
        major_version = int(version.split(".")[0])
        return major_version < config.NEW_CHROME_DRIVER_VER

    @classmethod
    def _download(cls, version: str) -> Path:
        if cls._is_old_version(version):
            file_relative_path = str(Path(version).joinpath(config.CHROME_DRIVER_FILE_NAME))
            download_url = urljoin(config.CHROME_DRIVER_URL, file_relative_path)
        else:
            file_name = config.NEW_CHROME_DRIVER_FILE_NAME.format(platform=config.CHROME_DRIVER_PLATFORM)
            chrome_driver_url = config.NEW_CHROME_DRIVER_URL.format(version=version, platform=config.CHROME_DRIVER_PLATFORM)
            download_url = urljoin(chrome_driver_url, file_name)
        res = cls._get(download_url)
        return cls._save_zip_to_tmp(res.content)

    @classmethod
    def _save_zip_to_tmp(cls, data: bytes) -> Path:
        file_name = ".".join([str(uuid.uuid4()), "zip"])
        path_to_write = cls.path_to_download.joinpath(file_name)
        path_to_write.write_bytes(data)
        return path_to_write

    @classmethod
    def _unzip(cls, archive_path: Path, version: str) -> str:
        archive = zipfile.ZipFile(file=archive_path)
        driver_file_path = cls.make_driver_full_path()
        if driver_file_path.exists():
            logger.info("Remove previouse driver at: %s", driver_file_path)
            driver_file_path.unlink()

        if cls._is_old_version(version):
            archive.extract(member=cls.driver_name, path=str(cls._path_to_store))
        else:
            zip_driver_file_path = f"{cls.zip_driver_path.format(platform=config.CHROME_DRIVER_PLATFORM)}/{cls.driver_name}"
            with open(cls._path_to_store.joinpath(cls.driver_name), "wb") as f:
                f.write(archive.read(zip_driver_file_path))

        archive.close()
        if not driver_file_path.exists():
            raise ChromeDriverLoaderException(
                f"Driver archive downloaded. "
                f'But file "{cls.driver_name}" not found in it.'
            )
        # set -rwxrwxr-x to file
        driver_file_path.chmod(0o775)
        return str(driver_file_path)
