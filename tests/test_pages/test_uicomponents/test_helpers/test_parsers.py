from combo_e2e.pages.uicomponents.helpers import parse_table_thead, parse_table_row

test_data = """
<tr>
    <th psortablecolumn="id"> #
        <p-sorticon _ngcontent-wlu-c2="" ng-reflect-field="id"><i class="ui-sortable-column-icon"></i>
        </p-sorticon>
    </th>
    <th psortablecolumn="name" ng-reflect-field="name">
        Name
    </th>
    <th _ngcontent-wlu-c2=""> Flag (push_disabled)</th>
</tr>
"""

test_row = """
<tr>
    <td _ngcontent-wyw-c2=""> 2</td>
    <td _ngcontent-wyw-c2=""> test Compaign</td>
    <td _ngcontent-wyw-c2=""><label><input type="checkbox"><span _ngcontent-wyw-c2="" class="switch-slider"
                                           data-e2e="enable_camp_2"></span></label>
    </td>
</tr>
"""


def test_parse_table_thead():
    res = parse_table_thead(test_data, 'text', {'ng-reflect-field', 'psortablecolumn'})

    assert 1 == res['text'].get('#')
    assert 1 == res['psortablecolumn'].get('id')
    assert 2 == res['text'].get('Name')
    assert 2 == res['ng-reflect-field'].get('name')
    assert 2 == res['psortablecolumn'].get('name')


def test_parse_table_row():
    res = parse_table_row(test_row)
    assert res[0] == '2'
    assert res[1] == 'test Compaign'
