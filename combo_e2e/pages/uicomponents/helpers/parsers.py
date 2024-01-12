from collections import defaultdict
from typing import List, Optional, Set, Union

from lxml import html
from lxml.html import HtmlElement

HEAD_COLUMN_TAG = "th"


def get_html_from_string(value: str) -> HtmlElement:
    return html.fromstring(value)


def get_multiple_html_elements_from_string(value: str) -> List[Union[HtmlElement, str]]:
    return html.fragments_fromstring(value)


def format_tag_text(text: str) -> str:
    if text is None:
        text = str(text)
    text = text.strip()
    return text.replace("\n", "")


def parse_table_thead(head: str, tag_text_key: str, attributes: Set[str]):
    """
    Parses table header and forms dict helper to get column index by its search-pattern
    (either visible text or the value of some attribute)
    :param head:
    :param tag_text_key:
    :param attributes:
    :return:
    """
    res = defaultdict(dict)
    index = 1
    head_elements: List[
        Union[HtmlElement, str]
    ] = get_multiple_html_elements_from_string(head)
    tr_elements: List[HtmlElement] = []

    for element in head_elements:
        if isinstance(element, str):
            continue
        if element.tag == "div":
            # thead conints not just tr with all the headers
            for item in element.iterchildren():
                if item.tag == "tr":
                    tr_elements.append(item)
        elif element.tag == "tr":
            tr_elements.append(element)

    if not tr_elements:
        raise ValueError("Table format could be changed")

    for tr_element in tr_elements:
        for item in tr_element.iterchildren():
            colspan = item.get("colspan")
            if colspan and int(colspan) > 1:
                # group title, not column name
                continue
            if item.tag == HEAD_COLUMN_TAG:
                formatted_key = format_tag_text(item.text)
                if tag_text_key in res and formatted_key in res[tag_text_key]:
                    raise ValueError(
                        f"Duplicate value={formatted_key} of th.text in header of table"
                    )
                res[tag_text_key][formatted_key] = index
                if attributes:
                    for name, value in item.items():
                        if value and name in attributes:
                            res[name][value] = index
                index += 1
    return res


def parse_table_row(row: str) -> List:
    """
    Parses table row (tr content) into a list (pulls out visual value of the cells)
    :param row:
    :return:
    """
    res = []
    obj: HtmlElement = get_html_from_string(row)
    if obj.tag != "tr":
        raise ValueError("It parse only tr tag content")
    for cell in obj.iterchildren():
        res.append(cell.text.strip() if cell.text else None)
    return res


def parse_table_cell(row: str) -> Optional[str]:
    """
    Parses table cell (td content) and pulls visible text out of it
    :param row:
    :return:
    """
    cell: HtmlElement = get_html_from_string(row)
    if cell.tag != "td":
        raise ValueError("It parse only td tag content")
    return cell.text.strip() if cell.text else None
