from typing import List
from unittest.mock import Mock

from combo_e2e.pages import ElementDescriptor, WebElementProxy, BaseNavigation, BaseNavigationMeta, BasePage


class MockWebElement:
    _click_call_count = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._click_call_count = 0

    def click(self):
        self._click_call_count += 1


class MockedElementDescriptor(ElementDescriptor):

    def _search_element(self, context):
        mocked = WebElementProxy(
            page=context,
            by='test',
            value='test',
            target_object=MockWebElement(),

        )
        if self.many:
            return [mocked]
        return mocked


class NavigationTestClass(BaseNavigation, metaclass=BaseNavigationMeta):
    page = 'test_page'

    nav_link: MockWebElement = MockedElementDescriptor(value='a', search_by='test')


class BaseTestClass(BasePage):
    page_url = 'test'
    _cached_attrs = None
    wait = Mock()

    # noinspection PyMissingConstructor
    def __init__(self):
        self._driver = Mock(window_handles=[])
        self._driver.current_url = 'test'
        self._cached_attrs = {}
        self._init_navigation_components()

    element: MockWebElement = MockedElementDescriptor(value='a', search_by='b')
    elements: List[MockWebElement] = MockedElementDescriptor(value='c', search_by='d', many=True)

    nav: NavigationTestClass = NavigationTestClass()

    def check_opened(self):
        pass


def test_navigation_class():
    base = BaseTestClass()
    nav_link = base.nav.nav_link
    nav_link.click()

    assert nav_link._click_call_count == 1
