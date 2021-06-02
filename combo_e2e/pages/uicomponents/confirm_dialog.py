from contextlib import suppress
from typing import Optional

from combo_e2e.helpers.exceptions import NoSuchElementError, ConfirmDialogNotFound, ConfirmDialogAttributeError, \
    ConfirmDialogException
from combo_e2e.pages import WebElementProxy
from combo_e2e.pages.uicomponents.helpers import format_xpath_from_parent
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement


class ConfirmDialog:
    tag_name = 'p-confirmdialog'
    _body_classes = ('p-dialog', 'ui-dialog')
    _title_class = 'p-dialog-title'
    _message_class = 'p-dialog-content'

    ok_btn_relative_xpath = '//button[@ng-reflect-label="Yes"]'
    cancel_btn_relative_xpath = '//button[@ng-reflect-label="No"]'

    component: WebElement = None
    """
    contains tag and its content converted into WebElement
    <div class="ui-dialog ...">...<div/>
    """

    def __init__(self, element: WebElementProxy):
        self._element = element
        if not isinstance(element, WebElementProxy):
            raise ConfirmDialogException('Wrapped object must be instance of WebElementProxy')
        if self.tag_name != element.tag_name:
            raise NoSuchElementError(f'ConfirmDialog element container must have tag="{self.tag_name}"')
        self.component = self._find_component(element)

    def _find_component(self, element: WebElementProxy) -> WebElement:
        for class_name in self._body_classes:
            with suppress(NoSuchElementException):
                return element.find_element_by_class_name(class_name)
        raise ConfirmDialogNotFound(f'Cannot find ConfirmDialog body by classes: {", ".join(self._body_classes)}. '
                                    f'Maybe ConfirmDialog is not visible.')

    @property
    def message(self):
        """
        Dialog main text
        :return:
        """
        return self._get_element_text(self._message_class)

    @property
    def title(self):
        """
        Dialog header text
        :return:
        """
        return self._get_element_text(self._title_class)

    @property
    def button_ok(self) -> WebElement:
        return self._find_child_by_xpath(self.ok_btn_relative_xpath)

    @property
    def button_cancel(self) -> WebElement:
        return self._find_child_by_xpath(self.cancel_btn_relative_xpath)

    def confirm(self):
        self.button_ok.click()
        self._element.page.wait_loaders_hidden()

    def cancel(self):
        self.button_cancel.click()
        self._element.page.wait_loaders_hidden()

    def _find_child_by_xpath(self, relative_xpath: str) -> WebElement:
        xpath = format_xpath_from_parent(relative_xpath)
        try:
            return self.component.find_element_by_xpath(xpath)
        except NoSuchElementException:
            raise ConfirmDialogAttributeError(f'Tag({xpath}) not found in parent tag of this element')

    def _get_element_text(self, css_class: str) -> Optional[str]:
        try:
            el = self.component.find_element_by_class_name(css_class)
            return el.text
        except NoSuchElementException:
            raise ConfirmDialogAttributeError(f'Cannot find ConfirmDialog attribute by class="{css_class}"')
