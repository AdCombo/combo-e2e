import logging
import re
import sys
from urllib.parse import urlsplit, urlencode, parse_qs

from combo_e2e.helpers.exceptions import ParserException
from lxml import html, etree
from lxml.html import HtmlElement
from pathlib import Path
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

PY_EXT = 'py'


class LineRange:
    """
    Helper class describing a range of integers, including boundary values.
    Simplifies checks like: c in range(a, b)
    """
    start = None
    end = None

    def __init__(self, start: int = 0, end: int = 0):
        self.start = start
        if end < start:
            raise ValueError('end must be greater than start')
        self.end = end

    def __contains__(self, line: int) -> bool:
        if not isinstance(line, int):
            raise ValueError(f'line must be integer value, got <{line}, {type(line)}>')
        if line > self.end or self.start > line:
            return False
        return True

    def __repr__(self):
        return f'<LineRange({self.start}, {self.end})>'

    def __str__(self):
        return f'range from {self.start} to {self.end}'


class Utils:
    """
    Class, containing majority of helper functions
    """
    @classmethod
    def get_html_from_file(cls, path: Path) -> HtmlElement:
        """
        Returns lxml.html object
        :param path:
        :return:
        """
        if not path.exists():
            raise ParserException(f'path "{path}" must be exist in project dir')

        with path.open('r') as f:
            data = f.read()
            try:
                return html.fromstring(data)
            except etree.ParserError as error:
                if error.args[0] != 'Document is empty':
                    raise error

    @classmethod
    def get_html_fragment_from_string(cls, data: str) -> HtmlElement:
        """
        Returns one first-level tag from the given string
        :param data:
        :return:
        """
        return html.fragment_fromstring(data)

    @classmethod
    def get_class_name_from_file_name(cls, file_name: Path) -> str:
        """
        Converts the file name to the corresponding python class name
        :param file_name:
        :return:
        """
        name_without_ext = file_name.stem
        new_name = cls.format_name_to_python_format(name=name_without_ext)
        name_parts = filter(lambda n: n.strip(), re.split(r'[_\W]+', new_name))
        return "".join(map(lambda s: s.capitalize(), name_parts))

    @classmethod
    def get_python_format_file_name(cls, file_name: Path) -> Path:
        """
        Converts the file name to the corresponding py file name
        :param file_name:
        :return:
        """
        name_without_ext = file_name.stem
        new_name = cls.format_name_to_python_format(name=name_without_ext)
        return Path(f'{new_name}.{PY_EXT}')

    @classmethod
    def format_name_to_python_format(cls, name: str) -> str:
        """
        converts a string to a valid variable/module name
        :param name:
        :return:
        """
        name = name.lower()
        if name[0].isdigit():
            name = f'p{name}'
        name_parts = filter(lambda n: n.strip(), re.split(r'[-_\W]+', name))
        new_name = "_".join(name_parts)
        return new_name

    @classmethod
    def path_with_row_number(cls, path: Path, raw_number: int) -> str:
        if not raw_number or raw_number < 1:
            raw_number = 'N/A'
        return f'{path}:{raw_number}'

    @classmethod
    def make_attribute_name(cls, tag_name: str, property_name: str) -> str:
        """
        Generates the name of a class attribute from the names of the tag and property that was searched
        :param tag_name:
        :param property_name:
        :return:
        """
        tag_name = cls.format_name_to_python_format(tag_name)
        return f'{tag_name}_{property_name}'

    @classmethod
    def create_module_dir(cls, module_path: Path) -> None:
        """
        Creates a folder with an init file, if there is no such module yet
        :param module_path: абсолютный путь до модуля
        :return:
        """
        if not module_path.exists():
            module_path.mkdir(parents=True)
        init_file = module_path.joinpath('__init__.py')
        if not init_file.exists():
            init_file.touch()

    @classmethod
    def get_module_path_by_class(cls, target_class) -> Path:
        """
        Returns the absolute path to the module by class from it
        :param target_class:
        :return:
        """
        return Path(sys.modules[target_class.__module__].__file__)


class RelativeImportPath:
    """
    A helper class that allows to build a relative import of classes from one module to another
    based on their absolute paths
    """
    @classmethod
    def get(cls, root: Path, to_path: Path, from_path: Path, class_names: List[str]) -> str:
        """
        Generates a relative import path
        :param root: both modules root
        :param to_path: absolute path to the module to import to
        :param from_path: absolute path to the module from which the class is imported
        :param class_names: имена классов, который нужно импортировать
        :return:
        """
        if from_path.stem == '__init__':
            from_path = from_path.parent
        from_path_relative = from_path.relative_to(root)
        to_path_relative = to_path.relative_to(root)
        for from_part, to_part in zip(from_path_relative.parts, to_path_relative.parts):
            if from_part != to_part:
                break
            root = root.joinpath(from_part)
        from_path_relative = from_path.relative_to(root)

        dots = cls._count_dots(root, to_path)
        import_path = ''.join([dots * '.', cls._path_to_import_notation(from_path_relative)])

        printed_class_names = ', '.join(class_names)

        return f'from {import_path} import {printed_class_names}'

    @classmethod
    def _count_dots(cls, root: Path, to_path: Path) -> int:
        """
        calculates the number of dots (subdirectories) between root and to_path
        :param root:
        :param to_path:
        :return:
        """
        base_folder = root.stem
        dots = 0
        for parent in to_path.parents:
            dots += 1
            if parent.stem.endswith(base_folder):
                break
        else:
            raise ParserException('impossible to build relative import from %s to %s', to_path, root)

        return dots

    @classmethod
    def _path_to_import_notation(cls, path: Path) -> str:
        """
        :param path: path to the py module
        :return:
        """
        to = []
        base = str(path.parent) if len(path.parts) > 1 else ''
        import_path = base.replace('/', '.')
        if import_path:
            to.append(import_path)

        module_name = path.stem
        to.append(module_name)

        return '.'.join(to)


class PageUrlHelper:
    """
    routes for js pages in an angular application are stored in a separate file,
    this parser generates a dict of the following format from a file with routes:
    {<relative_path_to_file>: <page_route>}
    """
    import_search_pattern = r"""import {\s*(?P<component>\w+)\s*} from ["'](?P<path>[.\/\-\w]+)["'];"""
    """
    search in: import {DefaultComponent} from "../../theme/pages/default/default.component";
    and return two groups: group1 - (DefaultComponent); group2 - (../../theme/pages/default/default.component)
    """
    path_map_pattern = r"""[\"']*path[\"']*:\s+[\"'](?P<route>[#\-\/\w]*)[\"'],
                           [ \n]+[\"']*component[\"']*:\s+(?P<component>[\w]+)"""
    """
    get path and component from:
    {
        "path": "tickets/tickets-details",
        "component": TicketsDetailComponent
    },
    """
    import_search_regex = re.compile(import_search_pattern)
    path_map_regex = re.compile(path_map_pattern, re.VERBOSE | re.MULTILINE)

    @classmethod
    def get_routes_map(cls, js_path: Path) -> Dict[str, str]:
        with js_path.open('r') as f:
            data = f.read()
            file_map = cls._search_file_map(data)
            path_map = cls._search_path_map(data)
            routes_map = {path: path_map.get(component, '') for component, path in file_map.items()}

        if not routes_map:
            logger.error('Routes for js-application not found in file: %s', js_path)
            pass
        return routes_map

    @classmethod
    def _search_file_map(cls, data: str) -> Dict[str, str]:
        res = {}
        for line in re.finditer(cls.import_search_regex, data):
            res[line.group('component')] = Path(line.group('path')).name
        return res

    @classmethod
    def _search_path_map(cls, data: str) -> Dict[str, str]:
        res = {}
        for line in re.finditer(cls.path_map_regex, data):
            res[line.group('component')] = line.group('route')
        return res


def get_parents_classes_attrs(bases):
    all_attrs = {}
    attrs_dict = {}

    for parent_class in reversed(bases):
        attrs_dict.update(parent_class.__dict__)

    for key, value in attrs_dict.items():
        if key.startswith('__') or callable(value):
            continue
        all_attrs[key] = value

    return all_attrs


def split_url_and_params(url: str) -> Tuple[str, str]:
    res = urlsplit(url)
    if not res.scheme:
        return url, ''
    base_url = f'{res.scheme}://{res.netloc}'
    if res.path:
        base_url = ''.join([base_url, res.path])
    return base_url, res.query or ''


def get_domain_from_url(url: str) -> str:
    res = urlsplit(url)
    return res.netloc


def get_base_url(url: str) -> str:
    base_url, _ = split_url_and_params(url=url)
    return base_url


def add_url_params(url: str, params: Dict) -> str:
    if not params:
        return url
    encoded_params = urlencode(params)
    delimiter = '&' if '?' in url else '?'
    return f'{url}{delimiter}{encoded_params}'


def format_id(id_form: str, default=None) -> Optional[int]:
    try:
        return int(id_form.strip())
    except Exception:
        return default


def get_id_from_url(url: str) -> Optional[int]:
    """
    Tries to find the object id in the link using the REST schema
    :return:
    """
    res = urlsplit(url)
    if res.query:
        params = parse_qs(res.query)
        if 'id' in params:
            return format_id(params['id'][0])
    if res.path:
        return format_id(res.path.split('/')[-1])


def get_param_from_url(url: str, param_name: str) -> Optional[List[str]]:
    """
    Returns a parameter from the url, if any
    :param url:
    :param param_name:
    :return:
    """
    res = urlsplit(url)
    if res.query:
        params = parse_qs(res.query)
        if param_name in params:
            return params[param_name]


def format_to_regex(value: str) -> str:
    return value.replace('.', r'\.')

def str_or_bool(value):
    if value in ['true', 'True', '1', 'yes', True, 1]:
        value = True
    elif value in ['false', 'False', '0', 'no', False, 0]:
        value = False
    return value
