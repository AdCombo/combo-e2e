from abc import ABCMeta
from typing import Dict, List, Optional
from urllib.parse import urljoin

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from combo_e2e.config import config
from combo_e2e.helpers.const import PAGE_READY_SCRIPT
from combo_e2e.helpers.exceptions import BasePageException, PageNotOpened
from combo_e2e.helpers.page_helper import check_js_condition_is_true
from combo_e2e.helpers.utils import (
    add_url_params,
    get_base_url,
    get_id_from_url,
    get_parents_classes_attrs,
    split_url_and_params,
)
from combo_e2e.pages.base_abstract import AbstractBasePage
from combo_e2e.pages.base_navigation import BaseNavigation
from combo_e2e.pages.uicomponents import ConfirmDialog, Toast


class BasePageMeta(ABCMeta):
    """
    Base metaclass that implements basic logic for creating page classes from raw classes
    """

    def __new__(mcs, class_name, bases, attrs):
        """
        Args:
            class_name (str): the name of the class being created
            bases (list of class): the parents of the class being created
            attrs (str => obj dict): the attributes as defined in the class
                definition

        Returns:
            A new class
        """
        new_attrs = {}
        all_attrs = get_parents_classes_attrs(bases)
        all_attrs.update(attrs)

        app_name = all_attrs.pop("app_name", None)
        if not app_name:
            raise BasePageException('Page object must have "app_name" attribute')

        app_config = config.BASE_APP_CONFIG.get(app_name)
        base_url = app_config.get("base_url")
        if not base_url:
            raise BasePageException(
                f"Base url not found in config for project {app_name}. Fix it!!!"
            )
        new_attrs["_base_url"] = base_url

        page_url = all_attrs.pop("page_url", None)
        if page_url is None:
            raise BasePageException(f'Page object must have "page_url" attribute')
        new_attrs["page_url"] = urljoin(base_url, page_url)

        valid_urls = all_attrs.pop("valid_urls", [])
        valid_urls.append(page_url)
        new_attrs["valid_urls"] = [urljoin(base_url, url) for url in valid_urls]

        new_attrs["has_page_ready_script"] = app_config.get(
            "has_page_ready_script", False
        )

        for attr_name in {
            "page_loader_css_class",
            "table_loader_css_class",
            "modal_visible_css_class",
        }:
            value = all_attrs.pop(attr_name, None) or app_config.get(attr_name)
            if value is None:
                raise BasePageException(
                    f"{attr_name} attribute must be set in config for current app {app_name}"
                )
            new_attrs[attr_name] = value

        new_attrs.update(all_attrs)

        new_class = type.__new__(mcs, class_name, bases, new_attrs)

        return new_class


class BasePage(AbstractBasePage):
    app_name: str = None
    """application name, set by the parser"""
    page_url: str = None
    """relative route of the page, set by the parser"""
    has_page_ready_script: bool = False
    """whether the e2eReady attribute needs to be checked after the page is loaded with selenium, set by the metaclass"""
    valid_urls: List[str] = []
    """relative routes that can also lead to this page (for example, the login here can have a logout)"""
    page_loader_css_class: str = None
    """
    css class for finding the page loader in the layout
    Set by the metaclass from config, if not overridden in the inheriting class
    """
    table_loader_css_class: str = None
    """
    css class for finding the table loader in the layout
    Set by the metaclass from config, if not overridden in the inheriting class
    """
    modal_visible_css_class: str = None
    """
    css class for finding an open popup on the page
    Set by the metaclass from config, if not overridden in the inheriting class
    """
    _base_url: str = None

    def __init__(
        self,
        fresh_session: bool = False,
        open_page: bool = True,
        query_params: Optional[Dict] = None,
        **kwargs,
    ):
        """

        :param fresh_session: whether it is necessary to clear the current browser session (delete cookies, etc.)
        :param open_page: If False, then the object will be created without opening the page in the browser
        :param query_params: dictionary that will be appended to the url as a query string
        :param kwargs:
        """
        super().__init__(fresh_session=fresh_session)
        if open_page:
            self.open(params=query_params)

        self._init_navigation_components()

    def _init_navigation_components(self):
        """
        initializes navigation components, if any
        :return:
        """
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, BaseNavigation):
                value._init_from_page(self)

    def open(self, custom_url: Optional[str] = None, params: Optional[Dict] = None):
        """
        By default opens the page_url of the page.
        :param custom_url: path, relative to domain (must be present in valid_urls)
        :param params: params to be added to query
        :return:
        """
        url = self._make_valid_url(custom_url, params)
        self._open(url=url)
        self.wait_loaders_hidden()

    def _search_in_valid_urls(self, pattern: str) -> str:
        base_url, params = split_url_and_params(pattern)
        for url in self.valid_urls:
            if base_url.rstrip("/") in url:
                return f"{url}?{params}" if params else url
        raise PageNotOpened(
            f'You want to open url by pattern="{pattern}" '
            f"but url not found in valid_urls: {self.valid_urls}"
        )

    def _make_valid_url(
        self, custom_url: Optional[str] = None, params: Optional[Dict] = None
    ) -> str:
        """
        Returns the requested link if it is present in valid_urls
        :param custom_url:
        :param params:
        :return:
        """
        url = self.page_url
        if custom_url:
            url = self._search_in_valid_urls(custom_url)
        if params:
            url = add_url_params(url, params)
        return url

    def check_opened(self):
        opened_url = get_base_url(self.opened_url)
        for url in self.valid_urls:
            if url.rstrip("/") in opened_url:
                return
        raise PageNotOpened(
            f"Get attr of {type(self).__name__}, but current url: {self.opened_url}"
        )

    def wait_page_loaded(self) -> None:
        try:
            if self.has_page_ready_script:
                self.wait.until(check_js_condition_is_true(PAGE_READY_SCRIPT))
        except TimeoutException:
            raise BasePageException(
                'Check that "e2eReady" attribute set by frontend on the current page.'
            )

    def wait_loader_not_visible(self) -> None:
        if self.page_loader_css_class:
            self.wait.until(
                EC.invisibility_of_element_located(
                    (By.CLASS_NAME, self.page_loader_css_class)
                )
            )

    def wait_tableloader_not_visible(self) -> None:
        if self.table_loader_css_class:
            self.wait.until(
                EC.invisibility_of_element_located(
                    (By.CLASS_NAME, self.table_loader_css_class)
                )
            )

    def wait_dialog_is_visible(self) -> None:
        attr_name = "role"
        attr_value = "dialog"
        search_pattern = (By.XPATH, f'//*[@{attr_name}="{attr_value}"]')
        self.wait.until(EC.visibility_of_element_located(search_pattern))

    def wait_modal_is_visible(self):
        if self.modal_visible_css_class:
            locator = (By.XPATH, f'//*[@class="{self.modal_visible_css_class}"]')
            self.wait.until(EC.visibility_of_element_located(locator))

    def find_element_by_data_e2e(self, value: str):
        """
        Public interface for finding an element by the data-e2e attribute.
        To be used only if object will be used once (for text checks, links, etc.).
        In other cases, usage of class elements is recomended.
        :param value:
        :return:
        """
        xpath = f'//*[@{config.DATA_E2E_ATTRIBUTE}="{value}"]'
        return self.find_element(By.XPATH, xpath)

    def extract_id_from_opened_url(self) -> Optional[int]:
        """
        Returns the id retrieved from the url of the current page, None if not found
        :return:
        """
        self.check_opened()
        return get_id_from_url(self.opened_url)

    def wait_and_get_toast(self) -> Toast:
        """
        Waits for toast to open on the page and returns it
        :return:
        """
        found_toasts: List[WebElement] = self.find_elements(By.ID, Toast.component_id)
        element: WebElement = self.wait_visibility_one_of_elements(found_toasts)
        return Toast(element)

    def is_toast_success(self) -> bool:
        """
        Checks if toast of success type appeared on the page.
        :return:
        """
        toast = self.wait_and_get_toast()
        return toast.is_success

    def get_confirm_dialog(self) -> ConfirmDialog:
        """
        Returns ConfirmDialog
        :return:
        """
        element = self.find_element(By.TAG_NAME, ConfirmDialog.tag_name)
        return ConfirmDialog(element)

    def is_toast_error(self) -> bool:
        """
        Checks if toast of error type appeared on the page.
        :return:
        """
        toast = self.wait_and_get_toast()
        return toast.is_error

    def is_toast_warning(self) -> bool:
        """
        Checks if toast of warning type appeared on the page.
        :return:
        """
        toast = self.wait_and_get_toast()
        return toast.is_warning
