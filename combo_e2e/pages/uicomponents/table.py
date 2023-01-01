from enum import Enum
from typing import Dict, List, Optional, Set, Type

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

from combo_e2e.config import config
from combo_e2e.helpers.exceptions import (
    BaseTableException,
    TableColumnNotFound,
    TableElementNotFound,
    TableRowNotFound,
)
from combo_e2e.pages import WebElementProxy
from combo_e2e.pages.uicomponents.helpers import (
    parse_table_cell,
    parse_table_row,
    parse_table_thead,
)

TABLE_TAG = config.DEFAULT_TABLE_TAG
NESTED_TABLE_TAG = config.NESTED_TABLE_TAG
TABLE_ATTRIBUTE = config.TABLE_E2E_ATTRIBUTE
HEAD_COLUMN_TAG = "th"


class SearchBy(Enum):
    """
    Search option to search coumn by
    """

    visible_name = 1
    attribute_name = 2


class Column:
    """
    Table columnt class
    """

    head_tag_name: str = HEAD_COLUMN_TAG
    """tag, inside the table, which contains value of the header of a particular column"""
    _attr_name: str = None
    """attribute name of the table which contains Column instance"""
    visible_name: str = None
    """column visible name (by default, this attribute is used to search for a column in the table)"""
    search_attr_name: str = None
    """additional way to search for a column by its attribute (attribute should be unique)"""
    search_attr_value: str = None
    """column attribute value"""
    table = None
    """parent table of the column"""
    relative_xpath: str = None
    """xpath relative to the parent table"""

    def __init__(
        self,
        visible_name: str,
        search_type: SearchBy = SearchBy.visible_name,
        attr_name: Optional[str] = None,
        attr_value: Optional[str] = None,
    ):
        """

        :param visible_name: column header text
        :param search_type: search type(by default, search by name is used)
        :param attr_name: additional attribute by which the column can be found (use if column header
        is not unique)
        :param attr_value: значение атрибута
        """
        self.visible_name = visible_name
        if search_type is SearchBy.visible_name:
            self.relative_xpath = self._compile_xpath_by_visible_name(self.visible_name)
        elif search_type is SearchBy.attribute_name:
            self.relative_xpath = self._compile_xpath_by_attribute_name(
                attr_name, attr_value
            )
            self.search_attr_name = attr_name
            self.search_attr_value = attr_value
        else:
            raise NotImplementedError(f"search_type {search_type} not implemented")

    def __get__(self, obj, objtype=None):
        if not issubclass(objtype, Table):
            raise BaseTableException("Column object must be attribute of Table obj")
        if self.table != obj:
            obj._head_search_attrs.add(
                self.search_attr_name
            ) if self.search_attr_name else None
            self.table = obj
        return self

    @classmethod
    def _compile_xpath_by_visible_name(cls, name: str):
        return f'//{cls.head_tag_name}[contains(text(),"{name}")]'

    def _compile_xpath_by_attribute_name(self, name: str, value: str):
        if not (value and name):
            raise BaseTableException(
                "attr_name and attr_value must be pass if search_type is attribute_name"
            )
        return f'//{self.head_tag_name}[@{name}="{value}"]'

    def __repr__(self):
        return f"Column({self.relative_xpath})"

    def __set_name__(self, owner, name):
        if not issubclass(owner, Table):
            raise RuntimeError(
                f"Column object must be attribute of Table obj. Current parent is {owner}"
            )
        self._attr_name = name

    def __call__(self, search_value: str) -> List[WebElementProxy]:
        """
        Finds all cells of a column containing part of the search_value string
        :param search_value:
        :return:
        """
        return self.table._find_column_cells_by_visible_text(self, search_value)

    def __getitem__(self, item: int) -> WebElementProxy:
        """
        Returns cell of a column by its index ()
        Возвращает ячейку колонки по её номеру (starts from 1)
        :param item:
        :return:
        """
        if not isinstance(item, int) or item < 1:
            raise BaseTableException("Column item index must be integer >= 1")
        return self.table._get_column_cell_by_index(self, item)

    def values(self) -> List:
        """
        Returns all column values (ordered down from heading)
        :return:
        """
        return self.table._get_column_values(self)

    def get_index_by_value(self, value: str) -> int:
        """
        Returns first cell index in column with given value
        :param value: cell text to search for in a column
        :return:
        """
        try:
            return self.values().index(value) + 1
        except TypeError:
            raise TableElementNotFound(
                f"Cell with given value doesn't exist in the column"
            )

    def get_row_by_value(self, value: str) -> List:
        """
        Returns list of values of the first row with given value in a column
        :param value: cell text to search for in a column
        :return:
        """
        index = self.get_index_by_value(value)
        return self.table.get_row_values_by_index(index)

    @property
    def index(self):
        """
        Column number in the table in order from left to right (starts from 1)
        :return:
        """
        return self.table.get_column_index(self)

    def click(self):
        """
        Click on the column heading. Mainly used for sorting.
        :return:
        """
        cell: WebElementProxy = self.table.get_item_by_xpath(self.relative_xpath)
        cell.click_and_wait()


class Table:
    """
    Class that gives access to tables.
    Working through descriptor protocol so should be used only inside page class definition.
    """

    _tag_name = None
    """table tag"""
    __attr_name = None
    """base page attribute name where table instance is stored"""
    nested_table = False
    """if table is nested"""
    page = None
    """link to the instance of the page where the table is located"""
    _table: WebElementProxy = None
    """table as a selenium WebElement, gives access to selenium interface"""

    search_by = By.XPATH
    """locator type to search table on a page by"""
    value = None
    """locator value"""

    _head_search_attrs: Set[str] = None
    """head element attributes to search for"""
    columns_indexes: Dict[str, Dict[str, int]] = None
    """column indexes found during table initialization"""
    real_column_count: int = 0
    """found columns count"""
    _head_tag_text_key: str = "text"
    """key, for the tag's visible text, by which index can be found from _head_search_attrs"""

    r_xpath_body = "//tbody"
    r_xpath_header = "//thead"
    r_xpath_rows = "//tr"
    r_xpath_cells = "/td"

    @classmethod
    def r_xpath_row(cls, index: int):
        """
        starts from 1
        :param index:
        :return:
        """
        return f"{cls.r_xpath_rows}[{index}]"

    @classmethod
    def r_xpath_column(cls, index: int):
        """
        starts from 1
        :param index:
        :return:
        """
        return f"{cls.r_xpath_rows}{cls.r_xpath_cells}[{index}]"

    @classmethod
    def r_xpath_cell(cls, row_index: int, column_index: int):
        """
        starts from 1
        :param row_index:
        :param column_index:
        :return:
        """
        return f"{cls.r_xpath_row(row_index)}{cls.r_xpath_cells}[{column_index}]"

    @classmethod
    def r_xpath_column_cells_contains_text(cls, column_index: int, text: str):
        return f'{cls.r_xpath_rows}{cls.r_xpath_cells}[contains(string(),"{text}") and position()={column_index}]'

    @classmethod
    def get_body_row_xpath(cls, index: int):
        return "".join([cls.r_xpath_body, cls.r_xpath_row(index)])

    @classmethod
    def get_header_xpath(cls, index: int):
        return "".join([cls.r_xpath_header, cls.r_xpath_row(index)])

    @classmethod
    def get_body_cell_row_xpath(cls, row_index: int, column_index: int):
        paths = [
            cls.r_xpath_body,
            cls.r_xpath_row(row_index),
            cls.r_xpath_cell(row_index, column_index),
        ]
        return "".join(paths)

    def __repr__(self):
        return f"Table({self._tag_name}, {self.value})"

    def __init__(
        self,
        search_value: str = None,
        search_attribute: str = TABLE_ATTRIBUTE,
        tag_name: str = TABLE_TAG,
        nested_table: bool = False,
    ):
        """
        Always returns first table found by given params
        :param search_value: attribute to search for
        :param search_attribute: additional attribute to search for
        :param tag_name: tag the table is enclosed in
        """
        if self.__class__ == Table:
            raise BaseTableException(
                "You must inherit from Table class. Do not use directly"
            )
        self.nested_table = nested_table
        self._head_search_attrs = set()
        self._tag_name = tag_name
        if search_value and not search_attribute:
            raise BaseTableException(
                "search_attribute and search_value must be set together"
            )
        if self.__attr_name is None:
            self.__attr_name = search_value
        self.value = self._compile_search_xpath(search_attribute, search_value)

    def _compile_search_xpath(self, attribute: str = None, value: str = None) -> str:
        if not value:
            return f"//{self._tag_name}"
        return f'//{self._tag_name}[@{attribute}="{value}"]'

    def __set_name__(self, owner, name):
        self.__attr_name = name

    def __get__(self, page, objtype=None):
        if page is None:
            return self
        page.check_opened()

        cached_attrs = page._cached_attrs
        if cached_attrs.get(self.__attr_name) is None:
            self.page = page
            self._table = self._search_table(page)
            self._parse_header()
            cached_attrs[self.__attr_name] = self
        return cached_attrs[self.__attr_name]

    def __getattr__(self, item):
        if self.page:
            return getattr(self.page, item)
        raise BaseTableException(
            f"{self.__class__.__name__} not initialized from Page object"
        )

    def _search_table(self, page):
        table = page._find_element(self.search_by, self.value)
        return WebElementProxy(
            target_object=table,
            page=page,
            by=self.search_by,
            value=self.value,
            attr_name=self.__attr_name,
        )

    def _parse_header(self):
        head_html = self._table.find_element(
            "xpath", f".{self.r_xpath_header}"
        ).get_attribute("innerHTML")
        self.columns_indexes = parse_table_thead(
            head_html, self._head_tag_text_key, self._head_search_attrs
        )
        self.real_column_count = len(
            self.columns_indexes.get(self._head_tag_text_key) or []
        )

    def get_column_index(self, column: Column) -> int:
        """
        Returns index of the column by visible text of the tag, or by the value of its attribute.
        Attribute value has the priority.
        :param column
        :return:
        """
        if column.search_attr_value:
            return self.columns_indexes.get(column.search_attr_name, {}).get(
                column.search_attr_value
            )
        col_index = self.columns_indexes.get(self._head_tag_text_key, {}).get(
            column.visible_name
        )

        if not col_index:
            raise BaseTableException(f"Cannot find index of {column} in {self}")

        return col_index

    def _get_column_cell_by_index(
        self, column: Column, row_index: int
    ) -> WebElementProxy:
        col_index = self.get_column_index(column)
        xpath = self.r_xpath_cell(
            row_index=row_index,
            column_index=col_index,
        )
        return self.get_item_by_xpath(xpath)

    def _find_column_cells_by_visible_text(
        self, column: Column, text: str
    ) -> List[WebElementProxy]:
        """
        Finds all column elements matching given text
        :param column:
        :param text:
        :return:
        """
        col_index = self.get_column_index(column)
        xpath = self.r_xpath_column_cells_contains_text(col_index, text)
        return self.get_items_by_xpath(xpath)

    def get_header_values(self, index: int = 1) -> List:
        """
        Returns values of the table header
        :param index:
        :return:
        """
        return self._get_row_values_by_index(index, for_header=True)

    def get_row_values_by_index(self, index: int) -> List:
        """
        Returns the value of the table row by its index (starts from 1, excluding header)
        :param index:
        :return:
        """
        return self._get_row_values_by_index(index)

    def _get_row_values_by_index(self, index: int, for_header: bool = False) -> List:
        xpath = (
            self.get_header_xpath(index)
            if for_header
            else self.get_body_row_xpath(index)
        )
        try:
            row_html = self.get_item_by_xpath(xpath).get_attribute("outerHTML")
        except TableElementNotFound:
            raise TableRowNotFound(f"Row with index {index} not found in table")
        return parse_table_row(row_html)

    def get_column_values_by_index(self, index: int) -> List:
        """
        Returns column value by its index
        :param index:
        :return:
        """
        if index > self.real_column_count:
            raise TableColumnNotFound(f"Column with index {index} not exists in table")
        xpath = self.r_xpath_column(index)
        try:
            cells = self.get_items_by_xpath(xpath)
        except TableElementNotFound:
            cells = []

        res: List = [parse_table_cell(c.get_attribute("outerHTML")) for c in cells]
        return res

    def _get_column_values(self, column: Column) -> List:
        """
        Returns all column values
        :param column:
        :return:
        """
        col_index = self.get_column_index(column)
        return self.get_column_values_by_index(col_index)

    def get_item_by_xpath(self, xpath: str) -> WebElementProxy:
        """
        finds first element of the table by xpath (relative to the table tag)
        :param xpath:
        :return:
        """
        xpath = "".join([self.value, xpath])
        try:
            el = self._table.find_element(By.XPATH, xpath)
        except NoSuchElementException:
            raise TableElementNotFound(
                f'Element not found by {By.XPATH} value: "{xpath}"'
            )
        return self._wrap_proxy(el, By.XPATH, xpath)

    def get_items_by_xpath(self, xpath: str) -> List[WebElementProxy]:
        """
        finds all matching table elements by xpath (relative to the table tag)
        :param xpath:
        :return:
        """
        xpath = "".join([self.value, xpath])
        try:
            elements = self._table.find_elements(By.XPATH, xpath)
        except NoSuchElementException:
            raise TableElementNotFound(
                f'Elements not found by {By.XPATH} value: "{xpath}"'
            )
        return [self._wrap_proxy(el, By.XPATH, xpath) for el in elements]

    def _wrap_proxy(self, element: WebElement, by, value) -> WebElementProxy:
        """
        Wraps a WebElement instance so that custom WebElementProxy functions are available
        :param element:
        :param by:
        :param value:
        :return:
        """
        return WebElementProxy(
            target_object=element,
            page=self._table.page,
            by=by,
            value=value,
        )


class ListOfNestedTables:
    """
    Class that stores and gives access to group of similar tables with same search_value but different indexes:
    <table name="nested_table_row_1"></table>
    <table name="nested_table_row_2"></table>
    Initialization: nested_tables = ListOfNestedTables(table_cls, search_value='nested_table_row')
    then nested tables can be accessed by indexes:
    nested_tables[1]
    nested_tables[2]
    """

    table_cls: Type[Table] = None
    """Class of table that describes group of tables"""
    search_value: str = None
    """attribute by which tables are grouped"""
    tag_name: str = None
    """tag name of a table"""
    tables: Dict[int, Table] = {}
    """dictionary containing group of tables"""
    page = None

    def __init__(
        self,
        table_cls: Type[Table],
        search_value: str,
        tag_name: str = NESTED_TABLE_TAG,
    ):
        """

        :param table_cls: Class of table that describes group of tables
        :param search_value: attribute by which tables are grouped
        :param tag_name: tag name of a table
        """
        self.table_cls = table_cls
        self.search_value = search_value
        self.tag_name = tag_name
        self.tables = {}
        self.page = None

    def __getitem__(self, index: int):
        if not isinstance(index, int):
            raise BaseTableException(
                "ListOfNestedTables support only number access to attributes"
            )
        return self.get(index)

    def __get__(self, obj, objtype=None):
        self.page = obj.page
        return self

    def get(self, index) -> Table:
        if index not in self.tables:
            self.tables[index] = self.table_cls(
                search_value=f"{self.search_value}{index}",
                tag_name=self.tag_name,
                nested_table=True,
            )
        return self.tables[index].__get__(self.page)
