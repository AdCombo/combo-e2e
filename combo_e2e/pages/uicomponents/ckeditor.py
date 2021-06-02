from combo_e2e.helpers.exceptions import CKEditorException
from combo_e2e.pages import WebElementProxy
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement


class CKEditorDescriptor:
    find_by = None
    """search type (xpath, css-class)"""
    value = None
    """element seach value (relative to CKEditor)"""
    __element_name = None

    def __init__(self, value, find_by=By.CLASS_NAME):
        """

        :param value:
        :param find_by:
        """
        self.__element_name = None
        self.value = value
        self.find_by = find_by

    def __set_name__(self, owner, name):
        self.__element_name = name

    def __get__(self, editor, objtype=None):
        if editor is None:
            return self
        editor.el.page.check_opened()

        cached_attrs = editor._cached_attrs
        if cached_attrs.get(self.__element_name) is None:
            cached_attrs[self.__element_name] = editor.get_child_by(self.find_by, self.value)
        return cached_attrs[self.__element_name]

    def __getattribute__(self, item):
        if hasattr(CKEditorDescriptor, item):
            return object.__getattribute__(self, item)
        raise AttributeError


class CKEditor:
    """
    Helper class to work with CKEditor interface elements (in angular: ckeditor).
    Wrapper for the layout creation component

    usage example:
    page = SomePage()
    ckeditor = CKEditor(page.ckeditor_mailing)
    """
    _tag_name = 'ckeditor'

    def __init__(self, element: WebElementProxy):
        """
        Saves the WebElementProxy instance inside and performs necessary checks
        :param element:
        """
        if element.tag_name.lower() != self._tag_name:
            raise CKEditorException(f'{self.__class__} only works on <{self._tag_name}> elements, '
                                    f'not on <{element.tag_name}>')
        if not isinstance(element, WebElementProxy):
            raise CKEditorException(f'{self.__class__} work only with WebElementProxy instance, '
                                    f'not {element.__class__}')
        self._cached_attrs = {}
        self.el = element

    def get_child_by(self, by, value):
        try:
            return self.el.find_element(by=by, value=value)
        except NoSuchElementException:
            raise CKEditorException('Cannot find selected tab')

    btn_cut: WebElement = CKEditorDescriptor('cke_button__cut')
    btn_copy: WebElement = CKEditorDescriptor('cke_button__copy')
    text_area: WebElement = CKEditorDescriptor('cke_contents_ltr')
    btn_bold: WebElement = CKEditorDescriptor('cke_button__bold')
    btn_center_text: WebElement = CKEditorDescriptor('cke_button__justifycenter_icon')
