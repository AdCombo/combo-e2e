"""
This class wraps date-picker(ngx-daterangepicker-material) input and allows to interact with it. 
Time is set accoring to client time zone!
"""
from datetime import date, datetime
from typing import Callable, Optional

from combo_e2e.helpers.exceptions import DatePickerNotFound, DatePickerException, DatePickerAttributeError
from combo_e2e.pages import WebElementProxy
from combo_e2e.pages.uicomponents.helpers import format_xpath_from_parent
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement


class AttributeDescriptor:
    value = None
    """xpath value relative to datepicker by which to search for the element"""
    __attribute_name = None
    """name of base page attribute that stores the descriptor instance"""

    def __init__(self, value=None):
        """
        :param value:
        """
        self.__attribute_name = None
        self.value = value
        self._validate_params()

    def _validate_params(self):
        if not self.value:
            raise DatePickerException('value param must be passed to AttributeDescriptor')

    def __set_name__(self, owner, name):
        self.__attribute_name = '_'.join([owner.__class__.__name__.lower(), name])

    def __get__(self, datepicker, objtype=None):
        if datepicker is None:
            return self
        datepicker.page.check_opened()

        return self._search_element(datepicker)

    def __getattribute__(self, item):
        if hasattr(AttributeDescriptor, item):
            return object.__getattribute__(self, item)
        raise AttributeError

    def _search_element(self, datepicker) -> WebElement:
        parent: WebElement = datepicker.component
        xpath = format_xpath_from_parent(self.value)
        try:
            return parent.find_element_by_xpath(xpath)
        except NoSuchElementException:
            raise DatePickerAttributeError(f'Attribute of datepicker not found by xpath: {xpath}')


class DatePicker:
    tag_name = 'ngx-daterangepicker-material'
    """tag name that contains the component"""
    body_class = 'md-drppicker'
    """name of the class by which datepicker body can be found"""
    component: WebElement = None
    """
    contains tag and its content converted into WebElement
    <ngx-daterangepicker-material>...</ngx-daterangepicker-material>
    """
    default_date_format = "%m-%d-%Y"
    default_time_format = "%d/%m/%Y %H:%M"

    def __init__(self, element: WebElementProxy):
        parent_element = element.find_element_by_xpath('./..')
        self.component = self._find_component(parent_element)
        self.picker_panel = self._find_picker_panel(self.component)
        self._input = element

    button_ok: WebElement = AttributeDescriptor('.//button[contains(text(), "ok") or contains(text(), "OK")]')
    active_picker: WebElement = AttributeDescriptor('.//td[contains(@class, "active")]')

    def _find_component(self, parent_element: WebElement) -> WebElement:
        try:
            xpath = format_xpath_from_parent(self.tag_name)
            return parent_element.find_element_by_xpath(xpath)
        except NoSuchElementException:
            raise DatePickerNotFound(f'<{self.tag_name}> tag not found in parent tag of this element')

    def _find_picker_panel(self, component: WebElement) -> WebElement:
        try:
            return component.find_element_by_class_name(self.body_class)
        except NoSuchElementException:
            raise DatePickerNotFound(f'Cannot find datepicker body by class {self.body_class}')

    @property
    def is_visible(self):
        return self.picker_panel.is_displayed()

    def show(self):
        if not self.is_visible:
            self._input.click()

    @property
    def page(self):
        """
        Paige containing the datepicker
        :return:
        """
        return self._input.page

    def _set_value(self, format_func: Callable, *func_args):
        self.show()
        value_to_set = format_func(*func_args)
        self._input.clear()
        self._input.send_keys(value_to_set)

    def set_time(self, from_time: datetime, to_time: Optional[datetime] = None, formatter: Optional[str] = None):
        """
        Sets time(or time period if both argumets passed) in the datepicker input, but does not apply it.
        :param from_time:
        :param to_time:
        :param formatter: see python strftime doc
        :return:
        """
        if to_time:
            self._set_value(self._format_time_range, from_time, to_time, formatter)
        else:
            self._set_value(self._format_time, from_time, formatter)

    def set_date(self, from_date: date, to_date: date = None, formatter: Optional[str] = None):
        """
        Sets date(or dates period if both argumets passed) in the datepicker input, but does not apply it.
        :param from_date:
        :param to_date:
        :param formatter: see python strftime doc
        :return:
        """
        if to_date:
            self._set_value(self._format_date_range, from_date, to_date, formatter)
        else:
            self._set_value(self._format_date, from_date, formatter)

    def set_date_and_apply(self, from_date: date, to_date: date = None, formatter: Optional[str] = None):
        """
        Main method to use. Opens datepicker, sets given date period and presses ok button(or clicks on 
        the date itself if no ok button present). 
        :param from_date:
        :param to_date: if None, from_date date will be set instead of period
        :param formatter: see python strftime doc
        :return:
        """
        self.set_date(from_date, to_date, formatter)
        is_range = to_date is not None
        self._apply_date(is_range=is_range)

    def _apply_date(self, is_range: bool):
        try:
            self.button_ok.click()
        except DatePickerAttributeError:
            if is_range:
                raise
            self.active_picker.click()

    def set_time_and_apply(self, from_time: datetime, to_time: datetime = None, formatter: Optional[str] = None):
        """
        Main method to use. Opens datepicker, sets given time period and presses ok button
        :param from_time:
        :param to_time: if None, from_time time will be set instead of period
        :param formatter: see python strftime doc
        :return:
        """
        self.set_time(from_time, to_time, formatter)
        self.button_ok.click()

    def _format_date_range(self, from_: date, to_: date, formatter: Optional[str]) -> str:
        return ' - '.join([self._format_date(from_, formatter), self._format_date(to_, formatter)])

    def _format_time_range(self, from_: datetime, to_: datetime, formatter: Optional[str]) -> str:
        return ' - '.join([self._format_time(from_, formatter), self._format_time(to_, formatter)])

    def _format_date(self, date_to_format: date, formatter: Optional[str]):
        return date_to_format.strftime(formatter or self.default_date_format)

    def _format_time(self, time_to_format: datetime, formatter: Optional[str]):
        return time_to_format.strftime(formatter or self.default_time_format)
