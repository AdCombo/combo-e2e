import logging

from enum import Enum
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from uuid import uuid4

import ujson as json
from combo_e2e.driver import E2EDriver
from combo_e2e.config import config
from selenium.common.exceptions import WebDriverException

logger = logging.getLogger(__name__)

class ActionTypes(Enum):
    screenshot = 1
    logs = 2


PARAMS = {
    ActionTypes.screenshot.value: {
        'extension': 'png',
        'path_attribute': 'SCREENSHOT_PATH',
        'file_prefix': 'screenshot',
    },
    ActionTypes.logs.value: {
        'extension': 'log',
        'path_attribute': 'CONSOLE_LOG_PATH',
        'file_prefix': 'log',
    }
}


def _generate_file_name(name_part: str, action_type: int):
    time_stamp = datetime.now().strftime('%Y-%m-%d_%H_%M_%S')
    file_name = '_'.join([PARAMS[action_type]['file_prefix'], name_part, time_stamp])
    ext = PARAMS[action_type]['extension']
    return f'{file_name}.{ext}'


def _append_uniq_postfix(file_name: str) -> str:
    file_name = Path(file_name)
    extension = file_name.suffix
    origin_name = file_name.stem
    postfix = uuid4().hex[:8]
    return f'{origin_name}_{postfix}.{extension}'


def _get_base_path(action_type: int):
    path = Path(getattr(config, PARAMS[action_type]['path_attribute']))
    if not path.exists():
        path.mkdir(parents=True)
    return path


def _get_write_path(name_part: str, rewrite: bool, action_type: int) -> str:
    base_path = _get_base_path(action_type)
    file_name = _generate_file_name(name_part, action_type)
    path = base_path.joinpath(file_name)

    if not rewrite and path.exists():
        new_name = _append_uniq_postfix(file_name)
        path = base_path.joinpath(new_name)

    logger.info(f'Generated path for screenshot/logs: {str(path)}')
    return str(path)


def take_screenshot(name_part: str = "", rewrite: bool = False) -> None:
    """
    Makes page screenshot at the time of its call
    :param name_part: part of the file name to which the date will be appended
    :param rewrite: overwrite file if it has already been created
    :return:
    """
    driver = E2EDriver.get_driver()
    try:
        path = _get_write_path(name_part=name_part, rewrite=rewrite, action_type=ActionTypes.screenshot.value)
        driver.save_screenshot(path)
    except WebDriverException as ex:
        logger.warning('Cannot save screenshot. Ex: %s', str(ex))
        pass


def save_browser_logs(name_part: str = "", rewrite: bool = False) -> None:
    """
    Gets the output of the browser console at the time of its call
    :param name_part:
    :param rewrite:
    :return:
    """
    driver = E2EDriver.get_driver()
    try:
        logs: List[Dict] = driver.get_log('browser')
    except WebDriverException as ex:
        logger.warning('Cannot save browser logs. Ex: %s', str(ex))
        return

    if logs:
        path = _get_write_path(name_part=name_part, rewrite=rewrite, action_type=ActionTypes.logs.value)
        with Path(path).open('w') as f:
            f.write(json.dumps(logs))
