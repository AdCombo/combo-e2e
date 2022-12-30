from combo_e2e.helpers.exceptions import BasePageException


class BaseNavigationMeta(type):
    """
    Base metaclass that implements basic logic for creating navigation items from "raw" classes.
    """

    def __new__(mcs, class_name, bases, attrs):
        new_class = type.__new__(mcs, class_name, bases, attrs)

        return new_class


class BaseNavigation:
    page = None
    """reference to the BasePage instance"""

    def __set_name__(self, owner, name):
        self.__navigation_name = name

    def _init_from_page(self, page):
        self.page = page

    def __getattr__(self, item):
        if self.page:
            return getattr(self.page, item)
        raise BasePageException(
            f"{self.__class__.__name__} not initialized from Page object"
        )
