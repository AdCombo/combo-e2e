combo-e2e
============

Python end-to-end testing for AngularJS projects

Installation
============

`pip install git+git://github.com/AdCombo/combo-e2e.git`

Usage
============

Before running e2e tests angular application needs to be parsed:
   
```python
from pathlib import Path
from typing import List, Dict
    
from combo_e2e.html_parser import AngularFormatParser
from combo_e2e.helpers.utils import PageUrlHelper


class AppParser(AngularFormatParser):
    app_name: str = 'app_name'

    project_path = Path('/root/project/path')
    # absolute path to the root of the project

    relative_e2e_path = Path('e2e')
    # path to the e2e folder, relative to project_path, will contain parsed pages
    
    relative_app_path: Path = Path('app_name/src/app/')
    # path to angular app, relative to project_path
    
    components_relative_path: Path = Path('')
    # pages path, relative to relative_app_path
    
    pages_routes_file_relative_path: Path = Path('app-routing.module.ts')
    # path to file with page routes, relative to relative_app_path


    @classmethod
    def create_navigation_components(cls):
        """
        Create base navigation components or pass if none
        """
        nav_css_patterns = ['toggle_menu_icon', ]
        nav_patterns_by_attr = ['routerLink', ]
        cls.create_side_nav(css_patterns=nav_css_patterns, patterns_by_attr=nav_patterns_by_attr)
        cls.create_head()

    @classmethod
    def custom_parse(cls):
        """
        Parse pages from given routes
        """
        routes_path = cls.app_path.joinpath(cls.pages_routes_file_relative_path)
        pages_routes: Dict[str, str] = PageUrlHelper.get_routes_map(js_path=routes_path)

        cls.parse_pages(pages_routes=pages_routes)


if __name__ == '__main__':
    app_parser = AppParser()
    app_parser.parse()
```

The parser will save "raw" and "editable" page classes into corresponding folders inside ``relative_e2e_path`` 

If needed, additional elements can be added to "editable" classes, like a Table with grouped elements:

```python
class TableExample(Table):
    id_ = Column('#')
    name = Column('Name')

    some_button: ListOfElementDescriptor = ListOfElementDescriptor(base_name_parts=[
        'some_button_row_',
        ])

    def __get__(self, obj, objtype=None) -> 'TableExample':
        return super().__get__(obj, objtype)

class ComponentExample(ComponentExampletRaw, metaclass=BasePageMeta):
    table_example: TableExample = TableExample('table_example')
```

Configuration file should be updated with an actual app configuration:

```python
from combo_e2e.helpers.base_config import BaseConfig
from combo_e2e.config import config

class Config(BaseConfig):
    BASE_APP_CONFIG = {
        'test_app': {
            'base_url': 'http://localhost:4200/',
            'page_loader_css_class': 'pageLoaderElement',
            'table_loader_css_class': 'tableLoaderElement',
            'modal_visible_css_class': 'modal fade in show',
            'has_page_ready_script': False,
        },
    }

config.update_from_custom_config(Config)
```
and imported into conftest alongside ``download_chromedriver`` fixture from ``combo_e2e.helpers.chromedriver_loader``

Then actual e2e test can be run:

```python
from e2e.pages.app_name.component_example import ComponentExample

def test_example():
    example_page = ComponentExample()
    first_id = example_page.table_example.id_[1].text
    name_values = example_page.table_example.name.values()
    
    assert first_id == '1'

    assert 'test_name' in name_values

    example_page.table_example.some_button[1].click_and_wait()
```