class check_js_condition_is_true(object):
    """Checking js condition"""

    def __init__(self, js_code: str):
        self.code = js_code

    def __call__(self, driver):
        result = driver.execute_script(self.code)
        if result is True:
            return True
        else:
            return False
