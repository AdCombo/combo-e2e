import datetime
import time
from contextlib import contextmanager
from pathlib import Path
from typing import ContextManager, List, Union

from combo_e2e.pages.base_abstract import AbstractBasePage

CHECK_RATE = 0.5


class FileWaitTimeout(Exception):
    pass


class FileWaiter:
    def __init__(
        self,
        directory_to_watch: Union[str, Path],
        ignored_extentions: List[str],
        increase_to: int,
        timeout: int,
    ):
        self._start_time: float = datetime.datetime.now().timestamp()
        self.directory_to_watch = directory_to_watch
        self.ignored_extentions = ignored_extentions
        self.increase_to = increase_to
        self.timeout = timeout
        self._new_files = []

    @property
    def new_files(self) -> List[Path]:
        return self._new_files

    def wait(self):
        max_time = self._start_time + self.timeout
        while datetime.datetime.now().timestamp() < max_time:
            self._new_files = self._get_latest_files()
            if len(self._new_files) >= self.increase_to:
                return
            time.sleep(CHECK_RATE)
        else:
            raise FileWaitTimeout(
                "Could not wait for the specified number of files to appear in the folder"
            )

    def _get_latest_files(self) -> List[Path]:
        new_paths = []
        for path in self.directory_to_watch.iterdir():
            if (
                path.is_file()
                and path.stat().st_ctime > self._start_time
                and path.suffix not in self.ignored_extentions
            ):
                new_paths.append(path)
        return new_paths


@contextmanager
def wait_new_files(
    page: AbstractBasePage,
    path: Union[str, Path] = None,
    ignored_extentions: List[str] = None,
    increase_to: int = 1,
    timeout: int = 10,
) -> ContextManager[FileWaiter]:
    if path is None:
        path = page.downloads_dir
    if ignored_extentions is None:
        ignored_extentions = (".crdownload",)
    waiter = FileWaiter(path, ignored_extentions, increase_to, timeout)
    yield waiter
    waiter.wait()
    # closing all tabs that might have been opened while downloading files
    page.focus_on_first_opened_tab()
