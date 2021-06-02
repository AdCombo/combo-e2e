class ParserException(Exception):
    pass


class E2EBaseException(Exception):
    pass


class TestSetupException(E2EBaseException):
    pass


class BasePageException(E2EBaseException):
    pass


class PageNotOpened(BasePageException):
    pass


class NoSuchElementError(E2EBaseException):
    pass


class UnexpectedTagError(E2EBaseException):
    pass


class BaseSelectException(E2EBaseException):
    pass


class BaseTableException(E2EBaseException):
    pass


class TableElementNotFound(BaseTableException):
    pass


class TableRowNotFound(TableElementNotFound):
    pass


class TableColumnNotFound(TableElementNotFound):
    pass


class DatePickerException(E2EBaseException):
    pass


class DatePickerNotFound(DatePickerException):
    pass


class DatePickerAttributeError(DatePickerException):
    pass


class ConfirmDialogException(E2EBaseException):
    pass


class ConfirmDialogNotFound(ConfirmDialogException):
    pass


class ConfirmDialogAttributeError(ConfirmDialogException):
    pass


class TabSetException(E2EBaseException):
    pass


class CKEditorException(E2EBaseException):
    pass


class InputMaskException(E2EBaseException):
    pass
