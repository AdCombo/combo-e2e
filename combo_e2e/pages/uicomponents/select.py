import time
from typing import List, Union

from selenium.common.exceptions import StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC

from combo_e2e.helpers.exceptions import (
    BaseSelectException,
    NoSuchElementError,
    UnexpectedTagError,
)
from combo_e2e.pages import WebElementProxy


class Select:
    """
    Helper class to work with select interface elements (in angular: ng-select).
    Implements interfaces for selecting an item from a list.

    usage example:
    page = CustomPage()
    user_select = Select(page.input_select_user)
    user_select.select_by_index(0)
    """

    _options_container_tag = "ng-dropdown-panel"
    _loader_class = "ng-spinner-loader"
    _option_class = "ng-option"
    _tag_name = "ng-select"
    _text_area_locator = (By.TAG_NAME, "input")

    def __init__(self, element: WebElementProxy):
        """
        Saves the WebElementProxy instance inside and performs necessary checks
        :param element:
        """
        if element.tag_name.lower() != self._tag_name:
            raise UnexpectedTagError(
                f"Select only works on <{self._tag_name}> elements, not on <{element.tag_name}>"
            )
        if not isinstance(element, WebElementProxy):
            raise BaseSelectException(
                f"Select work only with WebElementProxy instance, not {element.__class__}"
            )
        self.container = element
        multi = self.container.get_attribute("multiple")
        self.is_multiple = multi and multi != "false"

    @property
    def options(self) -> List[WebElement]:
        """
        Get list with all available options
        :return:
        """
        return self._find_options(
            By.XPATH, f'//*[contains(@class,"{self._option_class}")]'
        )

    def _find_options(self, by: str, value: str) -> List[WebElement]:
        """
        Searches for all ng-select options
        :param by:
        :param value:
        :return:
        """
        self.container.click()
        self.container.page_wait.until(
            EC.visibility_of_element_located((By.TAG_NAME, self._options_container_tag))
        )
        options = self.wait_options_loading(by=by, value=value)

        if len(options) == 1:
            try:
                is_empty = self._is_empty_option(options[0])
            except StaleElementReferenceException:
                self.container.page_wait.until(
                    EC.invisibility_of_element_located(
                        (By.CLASS_NAME, self._loader_class)
                    )
                )
                options = self.container.find_elements(by, value)
                is_empty = self._is_empty_option(options[0])
            if is_empty:
                return []

        return options

    def wait_options_loading(self, by: str, value: str) -> List:
        options = self.container.find_elements(by, value)
        option_text = str(options[0].text if options else "load").lower()
        timeout = 1
        while ("load" in option_text or "not found" in option_text) and timeout > 0:
            time.sleep(0.1)
            timeout -= 0.1
            options = self.container.find_elements(by, value)
            option_text = str(options[0].text if options else "load").lower()
        return options

    @classmethod
    def _is_empty_option(cls, option: WebElement) -> bool:
        option_classes = option.get_attribute("class")
        if "ng-option-disabled" in option_classes:
            return True
        return False

    def select_by_index(self, index: int) -> None:
        """
        Selects element by its index, starting with 0
        :param index:
        :return:
        """
        try:
            option = self.options[index]
            option.click()
        except IndexError:
            raise NoSuchElementError(f"Could not locate option with index {index}")

    def select_by_visible_id(self, obj_id: int, select_all: bool = False) -> None:
        """
        Selects option by its visible id.
        :param obj_id:
        :param select_all: select all found options if it is True and select is multiple
        :return:
        """
        text_id = f"[{obj_id}]"
        try:
            self.select_by_visible_text(
                text_id, select_all=select_all, filter_key=obj_id
            )
        except NoSuchElementError:
            raise NoSuchElementError(f"Could not locate option with id: {obj_id}")

    def select_by_visible_text(
        self, text, select_all: bool = False, filter_key: Union[str, int, None] = None
    ) -> None:
        """
        Selects option to be found by the given text
        :param text:
        :param select_all: select all found options if it is True and select is multiple
        :param filter_key:
        :return:
        """
        xpath = f'//*[contains(@class,"{self._option_class}") and contains(string(),"{text}")]'
        self._send_keys(value=filter_key or text)
        opts = self._find_options(By.XPATH, xpath)
        matched = False
        for opt in opts:
            self._select_option(opt)
            if self.is_multiple and select_all:
                matched = True
                continue
            return

        if not matched:
            raise NoSuchElementError(
                f"Could not locate option with visible text: {text}"
            )

    def _select_option(self, option: WebElement) -> None:
        if not option.is_selected():
            option.click()

    def _send_keys(self, value: Union[str, int]):
        """
        Send keys to select area if it need to filter
        :param value:
        :return:
        """
        text_area = self.container.find_element(*self._text_area_locator)
        if text_area:
            text_area.send_keys(value)
