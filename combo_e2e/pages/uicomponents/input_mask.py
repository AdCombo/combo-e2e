import random
import string
from typing import Optional

from combo_e2e.helpers.exceptions import UnexpectedTagError, InputMaskException
from combo_e2e.pages import WebElementProxy
from selenium.webdriver.common.by import By


class InputMask:
    """
    Class-helper to interact with p-inputmask elements
    """
    tag_name = 'p-inputmask'
    _text_area_locator = (By.XPATH, './input')

    def __init__(self, element: WebElementProxy):
        """
        :param element:
        """
        if element.tag_name.lower() != self.tag_name:
            raise UnexpectedTagError(f'InputMask only works on <{self.tag_name}> elements, not on <{element.tag_name}>')
        if not isinstance(element, WebElementProxy):
            raise InputMaskException(f'InputMask work only with WebElementProxy instance, not {element.__class__}')
        self.container = element

    def send_keys(self, value: str):
        """
        Set text to input
        :param value: text to set
        :return:
        """
        interactive_input = self.container.find_element(*self._text_area_locator)
        interactive_input.clear()
        interactive_input.send_keys(value)

    @property
    def value(self):
        interactive_input = self.container.find_element(*self._text_area_locator)
        return interactive_input.get_attribute('value')

    def get_mask(self) -> str:
        """
        return input mask
        :return:
        """
        return self.container.get_attribute('mask')

    @classmethod
    def _get_letter_case(cls, uppercase: Optional[bool] = None) -> str:
        if uppercase:
            return string.ascii_uppercase
        elif uppercase is False:
            return string.ascii_lowercase
        else:
            return string.ascii_letters

    def generate_valid_value(self, uppercase: Optional[bool] = None) -> str:
        """
        Works fine with numbers and latin symbols
        :param uppercase: if not set letters can be in uppercase or lowercase
        :return:
        """
        mask: str = self.get_mask()
        buf = []
        letters = self._get_letter_case(uppercase=uppercase)
        for ch in mask:
            if ch.isdigit():
                buf.append(random.choice(string.digits))
            elif ch.isalpha():
                buf.append(random.choice(letters))
            elif ch == '*':
                buf.append(random.choice(letters + string.digits))
        return ''.join(buf)
