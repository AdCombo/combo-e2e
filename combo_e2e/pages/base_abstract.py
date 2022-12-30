"""
In the AbstractBasePage class, general methods must be specified, as well as mandatory methods,
which will be called in WebElementProxy, ElementDescriptor and other classes,
describing objects placed on the page
"""
import re
import time
from abc import ABCMeta, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Set, Union

from selenium.common.exceptions import (ElementNotVisibleException,
                                        NoSuchCookieException,
                                        NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from combo_e2e.config import config
from combo_e2e.driver import E2EDriver
from combo_e2e.helpers import const
from combo_e2e.helpers.exceptions import BasePageException
from combo_e2e.helpers.utils import get_param_from_url
from combo_e2e.pages import ElementDescriptor, WebElementProxy
from combo_e2e.pages.uicomponents import Table


class ScrollPositions(Enum):
    start = "start"
    center = "center"
    end = "end"
    nearest = "nearest"


class AbstractBasePage(metaclass=ABCMeta):
    _cached_attrs: Dict = None
    """Cached page attributes (present until the page is reloaded)"""

    @abstractmethod
    def __init__(self, fresh_session: bool = False):
        """
        :param fresh_session: clear browser cookies
        """
        self._cached_attrs = {}
        self._driver = E2EDriver.get_driver(fresh_session=fresh_session)
        self._downloads_dir = E2EDriver.downloads_dir
        self.__wait = WebDriverWait(self._driver, config.WEB_DRIVER_WAIT)

    @abstractmethod
    def open(self, *args, **kwargs):
        ...

    def _open(self, url: str):
        # clearing cached items every time the page is refreshed
        self._cached_attrs = {}
        self._driver.get(url)
        self.wait_page_loaded()

    def open_redirect_url(self, url: str):
        self._cached_attrs = {}
        self._driver.get(url)

    @property
    def driver(self):
        return self._driver

    @property
    def downloads_dir(self):
        """
        The folder where Chrome will save files by default. If None, this param was not overridden in config
        and default folder will be used
        :return:
        """
        return self._downloads_dir

    @property
    def opened_url(self):
        return self._driver.current_url

    @abstractmethod
    def check_opened(self):
        ...

    @abstractmethod
    def wait_page_loaded(self):
        ...

    @abstractmethod
    def wait_loader_not_visible(self):
        ...

    @abstractmethod
    def wait_tableloader_not_visible(self):
        ...

    def wait_loaders_hidden(self):
        self.wait_loader_not_visible()
        self.wait_tableloader_not_visible()

    def _close_tabs(self, tabs: List[str]):
        for handle in tabs:
            self.driver.switch_to.window(handle)
            self.driver.close()

    def focus_on_last_opened_tab(self):
        """
        checks number of open tabs, moves driver focus on the last opened,
        closes the rest.
        Not to be used unnecessarily,
        Не использовать напрямую без надобности, since this method is automatically called
        in element.click() и element.click_and_wait()
        :return:
        """
        if len(self.driver.window_handles) > 1:
            self._cached_attrs = {}
            all_tabs: List = self.driver.window_handles
            tab_to_focus = all_tabs.pop(-1)
            self._close_tabs(all_tabs)
            self.driver.switch_to.window(tab_to_focus)

    def focus_on_first_opened_tab(self):
        """
        Checks number of open tabs and closes all, except the first one
        :return:
        """
        if len(self.driver.window_handles) > 1:
            self._cached_attrs = {}
            all_tabs: List = self.driver.window_handles
            tab_to_focus = all_tabs.pop(0)
            self._close_tabs(all_tabs)
            self.driver.switch_to.window(tab_to_focus)

    @property
    def wait(self) -> WebDriverWait:
        """
        Standart wait object
        :return:
        """
        return self.__wait

    def custom_wait(
        self, timeout: int = None, frequency: float = None
    ) -> WebDriverWait:
        """
        Custom wait (polling rate and maximum waiting time can be adjusted)
        :param timeout:
        :param frequency:
        :return:
        """
        kwargs = {
            "timeout": config.WEB_DRIVER_WAIT,
        }
        if timeout:
            kwargs["timeout"] = timeout
        if frequency:
            kwargs["poll_frequency"] = frequency

        return WebDriverWait(self._driver, **kwargs)

    def _find_element(self, by=By.ID, value=None) -> WebElement:
        element = self._driver.find_element(by, value)
        if not element:
            raise BasePageException(f'Element not found by {by} value: "{value}"')
        return element

    def _find_elements(self, by=By.ID, value=None) -> List[WebElement]:
        elements = self._driver.find_elements(by, value)
        if not elements:
            raise BasePageException(f'Elements not found by {by} value: "{value}"')
        return elements

    def reload_element(
        self, el: Union[WebElementProxy, List[WebElementProxy]]
    ) -> Union[WebElementProxy, List[WebElementProxy]]:
        """
        Reload element if it has disappeared from the session
        :el: the element to be reloaded
        :return:
        """
        many = False
        if isinstance(el, list):
            el = el[0]
            many = True
        if not isinstance(el, WebElementProxy):
            raise BasePageException("Element must be instance of WebElementProxy")

        if el.attr_name:
            self._cached_attrs.pop(el.attr_name, None)

        return (
            self.find_elements(*el.locator) if many else self.find_element(*el.locator)
        )

    def find_element(self, by=By.ID, value=None) -> WebElementProxy:
        """
        Public interface for finding unique object on the page by any pattern.
        To be used only to find object  that will be used once (for text checks, links, etc.).
        In other cases, usage of class elements is recomended.
        :param by:
        :param value:
        :return:
        """
        element = self._find_element(by, value)
        return self._wrap_proxy(element, by, value)

    def find_elements(self, by=By.ID, value=None) -> List[WebElementProxy]:
        """
        Public interface for finding multiple objects on a page by single pattern.
        To be used only to find object  that will be used once (for text checks, links, etc.).
        In other cases, usage of class elements is recomended.
        :param by:
        :param value:
        :return:
        """
        elements = self._find_elements(by, value)
        return [self._wrap_proxy(el, by, value) for el in elements]

    def _wrap_proxy(self, element: WebElement, by, value) -> WebElementProxy:
        """
        Wraps a WebElement instance so that custom WebElementProxy functions are available
        :param element:
        :param by:
        :param value:
        :return:
        """
        return WebElementProxy(
            target_object=element,
            page=self,
            by=by,
            value=value,
        )

    def scroll_to_element(
        self,
        element: WebElementProxy,
        vertical_position: ScrollPositions = ScrollPositions.center,
        horizontal_position: ScrollPositions = ScrollPositions.nearest,
    ):
        """
        Scrolls the page to the passed element
        :param element: The element to scroll to
        :param vertical_position: Vertical scroll position
        :param horizontal_position: Horizontal scroll position
        :return:
        """
        script = const.SCROLL_TEMPLATE_SCRIPT.format(
            block=vertical_position.value, inline=horizontal_position.value
        )
        self.driver.execute_script(script, element)

    @classmethod
    def wait_visibility_one_of_elements(
        cls,
        elements: List[Union[WebElementProxy, WebElement]],
        timeout: Optional[int] = None,
        ticks: Optional[float] = 0.5,
    ) -> Union[WebElementProxy, WebElement]:
        """
        Waits for one of the passed elements to become visible to the user (located in the DOM)
        :param elements: List of elements to wait
        :param timeout: timeout
        :param ticks: polling rate (by default - once every half a second)
        :return:
        """
        if not elements:
            raise NoSuchElementException(
                "Nothing to wait. At least one element must be passed"
            )
        timeout = timeout or config.WEB_DRIVER_WAIT
        run_time = timeout

        while run_time > 0:
            for el in elements:
                if el.is_displayed():
                    return el
            time.sleep(ticks)
            run_time -= ticks
        raise ElementNotVisibleException(
            "Could not wait for the visibility of any of transmitted elements"
        )

    def delete_cookies(
        self, filter_value: Optional[str] = None, cookie_key: str = "name"
    ) -> None:
        """
        Clear cookies in current browser session
        :param filter_value: clear all browser cookies for current domain if it not passed. Value support regex
        :param cookie_key: key of cookie to clear. Name of cookie by default
        :return:
        """
        if filter_value is None:
            self.driver.delete_all_cookies()
        else:
            cookies: Set[Dict] = self.driver.get_cookies()
            for item in cookies:
                try:
                    cookie_value = item[cookie_key]
                except KeyError:
                    raise NoSuchCookieException(
                        f"Not found cookie by (value, key) = ({filter_value}, {cookie_key})"
                    )
                if re.search(filter_value, cookie_value, flags=re.IGNORECASE):
                    self.driver.delete_cookie(name=item["name"])

    def delete_local_storage(self, key: Optional[str] = None) -> None:
        """
        Clear local storage in current browser session
        :param key: clear all browser local storage if it not passed. Value support regex
        :return:
        """
        if key:
            self.driver.execute_script(
                "window.localStorage.removeItem(arguments[0]);", key
            )
        else:
            self.driver.execute_script("window.localStorage.clear();")

    def wait_accessibility_of(
        self,
        element_descriptor: Union[ElementDescriptor, WebElementProxy, Table],
        timeout: int = None,
        frequency: float = 0.2,
    ) -> None:
        """
        Waits for element to appear on the page
        :param element_descriptor: elements descriptor
        :param timeout: timeout (seconds)
        :param frequency: polling rate (seconds)
        :return:
        """
        if not isinstance(element_descriptor, (ElementDescriptor, Table)):
            raise BasePageException("It wait only Element Descriptor instance objects")
        search_pattern = (element_descriptor.search_by, element_descriptor.value)
        self.custom_wait(timeout, frequency).until(
            EC.visibility_of_element_located(search_pattern)
        )

    def extract_param_from_opened_url(self, name: str) -> Optional[str]:
        """
        Returns param extracted from the url of the current page. None if it could not be found
        :param name:
        :return:
        """
        self.check_opened()
        res = get_param_from_url(url=self.opened_url, param_name=name)
        if res:
            return res[0]

    def wait_element_clickable(self, element_descriptor: Union[ElementDescriptor, WebElementProxy, Table],
                               timeout: int = None, frequency: float = 0.2) -> None:
        """
        Waits for element to checking an element is visible and enabled such that you can click it
        :param element_descriptor: elements descriptor
        :param timeout: timeout (seconds)
        :param frequency: polling rate (seconds)
        :return:
        """
        if not isinstance(element_descriptor, (ElementDescriptor, Table)):
            raise BasePageException('It wait only Element Descriptor instance objects hz what is that')
        search_pattern = (element_descriptor.search_by, element_descriptor.value)
        self.custom_wait(timeout, frequency).until(EC.element_to_be_clickable(search_pattern))
