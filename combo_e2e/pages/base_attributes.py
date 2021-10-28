"""
In this module, when accessing the attributes of page objects, only methods and attributes described
in AbstractBasePage can be used
"""
from functools import wraps
from inspect import ismethod
from typing import Tuple, List, Set

from combo_e2e.config import config
from combo_e2e.helpers.exceptions import BasePageException
from selenium.common.exceptions import StaleElementReferenceException, WebDriverException, NoSuchElementException
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

DATA_E2E_ATTRIBUTE_NAME = config.DATA_E2E_ATTRIBUTE


class WebElementProxyException(Exception):
    def __init__(self, msg=None, element=None):
        self.msg = msg
        self.element = element

    def __str__(self):
        exception_msg = "Message: %s\n" % self.msg
        if self.element is not None:
            exception_msg += "Occurred at element: %s" % self.element
        return exception_msg


class WebElementProxy(WebElement):
    """
    This class proxies access to the WebElement instance, implementing additional logic,
    to ensure that angular application was loaded
    """
    page = None
    """through this attribute, all methods of the BasePage page can be accessed"""
    _obj: WebElement = None
    """contains instance of the WebElement class, access to which is proxied"""
    locator: Tuple[str, str] = None
    """string representation for repeated element search (required in some WebElement methods)"""
    attr_name: str = None
    """the name of the attribute in the page that this object is associated with
    (set only if the object is received via a handle)"""

    # noinspection PyMissingConstructor
    def __init__(self, page, by, value, target_object, attr_name=None):
        if isinstance(target_object, WebElementProxy):
            raise BasePageException('target_object already is instance WebElementProxy')
        object.__setattr__(self, 'page', page)
        object.__setattr__(self, '_obj', target_object)
        object.__setattr__(self, 'locator', (by, value))
        object.__setattr__(self, 'attr_name', attr_name)

    def __getattribute__(self, name: str):
        if proxy_has_attr(name):
            attr = object.__getattribute__(self, name)
        else:
            attr = getattr(self._obj, name)

        if ismethod(attr) and not name.startswith('__'):
            decorator = catch_not_attach_to_session(self)
            return decorator(attr)
        return attr

    def __setattr__(self, name, value):
        if proxy_has_attr(name):
            object.__setattr__(self, name, value)
            return
        setattr(self._obj, name, value)

    def __delattr__(self, name):
        if proxy_has_attr(name):
            object.__delattr__(self, name)
            return
        return delattr(self._obj, name)

    @property
    def value(self):
        return self._obj.get_attribute('value')

    def until(self, condition, *args, **kwargs):
        self.page.wait.until(
            condition(self.locator, *args, **kwargs)
        )

    def until_not(self, condition, *args, **kwargs):
        self.page.wait.until_not(
            condition(self.locator, *args, **kwargs)
        )

    def click(self, focus_on_opened_tab: bool = True):
        """
        wait for the element to be available and click on it 
        (does not wait for the completion of something after the click)
        :focus_on_opened_tab: Whether it is needed to focus on a new tab if it's going to be open
        :return:
        """
        self.until(EC.element_to_be_clickable)
        self._obj.click()
        if focus_on_opened_tab:
            self.page.focus_on_last_opened_tab()

    def click_and_wait(self, focus_on_opened_tab: bool = True):
        """
        performs a standard click on the element, but after click waits for the completion of the running action.
        Completion signal - no page and table loaders
        :focus_on_opened_tab: Whether it is needed to focus on a new tab if it's going to be open
        :return:
        """
        self.click(focus_on_opened_tab=focus_on_opened_tab)
        self.page.wait_loaders_hidden()

    @property
    def page_wait(self):
        """
        implements access to the wait object of the page, if waiting for something needs to be implemented
        :return:
        """
        return self.page.wait

    def _reload_target_object(self) -> None:
        """
        Overloads the original WebElement. It is necessary, because elements even on an unreloaded page can be removed
        from the selenium session (this happens because in almost any action angular removes and adds DOM elements)
        :return:
        """
        if self.attr_name and self.attr_name in self.page._cached_attrs:
            self.page._cached_attrs.pop(self.attr_name, None)
        obj = self.page._find_element(*self.locator)

        object.__setattr__(self, '_obj', obj)
        # adding element back to the page cache, so that it won't be searched again while accessed next time
        # thought the descriptor
        if self.attr_name:
            self.page._cached_attrs[self.attr_name] = self


def get_subclass_attributes() -> Set[str]:
    """
    Helper that returns attribute names only of the WebElementProxy proxy class
    :return:
    """
    if hasattr(get_subclass_attributes, '__cached_attrs'):
        return get_subclass_attributes.__cached_attrs

    bases = WebElementProxy.__bases__
    if len(bases) > 1:
        raise NotImplemented('It works only with one parent classes')
    attrs = set(WebElementProxy.__dict__.keys())
    setattr(get_subclass_attributes, '__cached_attrs', attrs)
    return attrs


def proxy_has_attr(name: str) -> bool:
    """
    Same as hasattrs for WebElementProxy, implemented outside the class to avoid looping
    in the __getattribute method__
    :param name:
    :return:
    """
    if name in get_subclass_attributes():
        return True
    return False


def catch_not_attach_to_session(current_obj: WebElementProxy):
    """
    a decorator that allows WebElement instance overloading if it disappears from the browser session.
    the WebElement instance is stored in the WebElementProxy object, so we overload
    only selenium object, while the WebElementProxy instance remains the same, which allows
    to avoind BasePage objects recreation
    :param current_obj:
    :return:
    """
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except StaleElementReferenceException:
                current_obj._reload_target_object()
                return function(*args, **kwargs)
            except NoSuchElementException:
                raise
            except WebDriverException as ex:
                raise WebElementProxyException(str(ex), current_obj.attr_name or 'Object didnt attach to Page')

        return wrapper

    return decorator


class ElementDescriptor:
    """
    Descriptor for WebElementProxy. Allows to implement WebElement lazy loading,
    i. e. the selenium object is created only when class attribute is accessed through this descriptor.
    """
    search_by = None
    """element search type (by xpath, class, etc.)"""
    value = None
    """the value by which element is searched"""
    many = None
    """whether several elements will be found on the page for this pattern"""
    __element_name = None
    """the name of the base page attribute that stores the descriptor instance"""

    def __init__(self, search_by=None,
                 value=None,
                 many=False):
        """
        The only available method to pass parameters for searching for a web element on a page
        :param search_by: locator type (default: xpath)
        :param value: locator value
        :param many: flag that several elements will be found by the passed locator
        """
        self.__element_name = None
        self.search_by = search_by
        self.value = value
        self.many = many
        if self.value and not self.search_by:
            self.search_by = By.XPATH
        self._validate_params()

    def _validate_params(self):
        if not self.search_by or not self.value:
            raise BasePageException('[value, search_by] param must be passed to ElementDescriptor')

    def __set_name__(self, owner, name):
        self.__element_name = name

    def __get__(self, page, objtype=None):
        if page is None:
            return self
        page.check_opened()

        cached_attrs = page._cached_attrs
        if cached_attrs.get(self.__element_name) is None:
            cached_attrs[self.__element_name] = self._search_element(page)
        return cached_attrs[self.__element_name]

    def __getattribute__(self, item):
        if hasattr(ElementDescriptor, item):
            return object.__getattribute__(self, item)
        raise AttributeError

    def _search_element(self, page):
        if self.many:
            elements = page._find_elements(self.search_by, self.value)
            proxy_elements = []
            for item in elements:
                proxy_elements.append(
                    WebElementProxy(
                        target_object=item,
                        page=page,
                        by=self.search_by,
                        value=self.value,
                        attr_name=self.__element_name,
                    )
                )
            return proxy_elements

        web_element = page._find_element(self.search_by, self.value)
        return WebElementProxy(
            target_object=web_element,
            page=page,
            by=self.search_by,
            value=self.value,
            attr_name=self.__element_name,
        )


class ListOfElementDescriptor:
    """
    A descriptor class similar to ElementDescriptor, but to describe a group of elements,
    which differ in indices.
    <button name="row_1"></button>
    <button name="row_2"></button>
    This class is needed in order not to multiply the description of such elements in the base page.
    Allows you to describe the elements above like this:
    elements = ListOfElementDescriptor(base_name_parts=['row_'])
    and then any element can be accessed like this:
    elements.get(1)
    elements.get(2)
    Also allows to describe elements like this:
    <button name="row_1_foo"></button>
    <button name="row_2_foo"></button>
    You can use end_name_part parametr:
    elements = ListOfElementDescriptor(base_name_parts=['row_'], end_name_part='_foo')
    """
    base_name_parts: list = None
    """list of common parts of the attribute value of group of elements"""
    end_name_part: str = None
    """the end part of the attribute value of group of elements"""
    tag_attr_name: str = None
    """attribute name by which elements are grouped"""
    many: bool = None
    """flag that multiple elements will be found by full name"""
    page = None
    # only xpath search is supported for now
    search_by: str = 'xpath'

    def __init__(self, base_name_parts: List[str], end_name_part: str = None, many: bool = False,
                 tag_attr_name: str = DATA_E2E_ATTRIBUTE_NAME, context=None):
        """

        :param base_name_parts: list of common parts of the attribute value of group of elements
        :param end_name_part: the end part of the attribute value of group of elements
        :param many: flag that multiple elements will be found by full name
        :param tag_attr_name: attribute name by which elements are grouped
        :param context:
        """
        if not isinstance(base_name_parts, list):
            raise BasePageException('base_name_parts must be list of string')
        self.base_name_parts = [name.strip('_') for name in base_name_parts]
        self.end_name_part = end_name_part.strip('_') if end_name_part else end_name_part
        self.many = many
        self.tag_attr_name = tag_attr_name
        self.page = context

    def get_by_index(self, *numbers) -> WebElementProxy:
        """
        Get an element by its index on the rendered page. Is an interface to get method,
        which restricts numbers to only int type
        :param numbers:
        :return:
        """
        if not all([isinstance(num, int) for num in numbers]):
            raise BasePageException('all of parameters must be int')
        return self.get(*numbers)

    def get_no_load(self, *numbers) -> ElementDescriptor:
        """
        Returns element descriptor.
        Main usage: waiting for the element to appear on the page
        To do this, the descriptor must be passed to the page's wait_accessibility_of () method
        :return:
        """
        attr_name = self._make_attr_name(numbers)
        return self._get_attribute_descriptor(attr_name)

    def get(self, *numbers) -> WebElementProxy:
        """
        Fills base_name_parts with numbers and returns matching item, if any
        :param numbers: list of dynamic parameters to be combined with base_name_parts
        :return:
        """
        attr_name = self._make_attr_name(numbers)
        descriptor = self._get_attribute_descriptor(attr_name)
        return descriptor.__get__(self.page)

    def get_relative(self, *numbers) -> WebElementProxy:
        attr_name = self._make_attr_name(numbers)
        value = self._print_search_value(attr_name)
        return self.page.get_item_by_xpath(value)

    def _get_attribute_descriptor(self, attr_name: str) -> ElementDescriptor:
        if attr_name not in self.page.__dict__:
            descriptor = self._construct_attribute_descriptor(attr_name)
            setattr(self.page, attr_name, descriptor)
        return getattr(self.page, attr_name)

    def _construct_attribute_descriptor(self, attr_name: str) -> ElementDescriptor:
        value = self._print_search_value(attr_name)
        descriptor = ElementDescriptor(search_by=self.search_by, value=value, many=self.many)
        descriptor.__set_name__(None, attr_name)
        return descriptor

    def _print_search_value(self, attr_name: str) -> str:
        return f'//*[@{self.tag_attr_name}="{attr_name}"]'

    def _make_attr_name(self, args):
        params = list(map(str, args))
        if len(params) != len(self.base_name_parts):
            raise BasePageException(f'You pass to get method only {len(params)} params '
                                    f'but required {len(self.base_name_parts)}')

        indexed_names = []
        for val in zip(self.base_name_parts, params):
            indexed_names.append(('_' if val[0] else '').join(val))

        if self.end_name_part:
            indexed_names.append(self.end_name_part)

        return '_'.join(indexed_names)

    def __get__(self, page, objtype=None):
        self.page = page
        return self

    def __getitem__(self, item: int):
        if not isinstance(item, int):
            raise BasePageException('ListOfElementDescriptor support only number access to attributes')
        if getattr(self.page, 'nested_table', None) is True:
            return self.get_relative(item)
        return self.get(item)
