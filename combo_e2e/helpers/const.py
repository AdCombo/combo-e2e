PAGE_PATH_NAME = "pages"
RAW_PAGE_PATH_NAME = "raw_pages"
NAV_PAGE_PATH_NAME = "navigation"
RAW_PAGE_CLASS_POSTFIX = "Raw"

PAGE_READY_SCRIPT = "if ('e2eReady' in window && window.e2eReady === true){return true;}else{return false;}"

SCROLL_TEMPLATE_SCRIPT = """
arguments[0].scrollIntoView({{block: "{block}", inline: "{inline}"}})
"""
