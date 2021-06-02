from enum import Enum
from typing import Optional, Union

from combo_e2e.pages import WebElementProxy
from lxml.html import HtmlElement

from combo_e2e.helpers.exceptions import NoSuchElementError
from combo_e2e.pages.uicomponents.helpers.parsers import get_html_from_string
from selenium.webdriver.remote.webelement import WebElement


class _ToastTypes(Enum):
    error = 'adc-toast-error'
    info = 'adc-toast-info'
    success = 'adc-toast-success'
    warning = 'adc-toast-warning'


class Toast:
    """
    This class caches html representaion of popped out notification, allows access to its main components: 
    header, main text, nofitication type (success, error, info etc.), but doesn't allow interaction on the page
    because notification disappears and leaving following structure behind:
    <toaster-container>
        <div id="toast-container"><!----></div>
    </toaster-container>
    NoSuchElementError is raised if passed element linked with already disappeared notification
    """
    component_id = 'adc-toast-container'
    _component_class = 'adc-toast'
    _title_class = 'adc-toast-title'
    _message_class = 'adc-toast-body'

    component: HtmlElement = None
    """
    contains tag and its content converted into HtmlElement
    <div toastcomp="" class="toast"><div/>
    """

    Types = _ToastTypes

    def __init__(self, element: Union[WebElement, WebElementProxy]):
        self._element = element
        self._outer_html: HtmlElement = get_html_from_string(element.get_attribute('outerHTML'))
        if self.component_id != element.get_attribute('id'):
            raise NoSuchElementError(f'Toast element container must have id="{self.component_id}".')

        self.component = self._get_base_element()
        self._type = self._get_type()

    def _get_base_element(self):
        component = self._outer_html.find_class(self._component_class)
        if not component:
            raise NoSuchElementError(f'Toast element disappeared from the page when the object was created')
        return component[0]

    def _get_type(self):
        for t in self.Types:
            if t.value in self.component.classes:
                return t
        return None

    def hide(self):
        """
        Hides notification by clicking on it
        :return:
        """
        if self._element.is_displayed():
            self._element.click()

    @property
    def type(self):
        """
        Notification type
        :return:
        """
        return self._type

    @property
    def is_success(self):
        """
        Check if notification type is success
        :return:
        """
        return self.type and self.type is self.Types.success

    @property
    def message(self):
        """
        Notification main text
        :return:
        """
        return self._get_element_text(self._message_class)

    @property
    def title(self):
        """
        Notification header text
        :return:
        """
        return self._get_element_text(self._title_class)

    def _get_element_text(self, css_class: str) -> Optional[str]:
        tag: Optional[HtmlElement] = self.component.find_class(css_class)
        if tag:
            return str(tag[0].text_content())

    @property
    def is_error(self):
        """
        Check if notification type is error
        :return:
        """
        return self.type and self.type is self.Types.error
