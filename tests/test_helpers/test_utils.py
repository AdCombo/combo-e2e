from pathlib import Path

from combo_e2e.helpers.utils import Utils, RelativeImportPath


class TestUtils:

    def test_get_class_name_from_file_name(self):
        file_name = Path('aside-nav.component.html')
        expected_name = 'AsideNavComponent'

        assert expected_name == Utils.get_class_name_from_file_name(file_name)


class TestRelativeImportPath:
    def test__path_to_import_notation(self):
        path = Path('test/path/path2/test.py')
        expected = 'test.path.path2.test'

        assert expected == RelativeImportPath._path_to_import_notation(path)
