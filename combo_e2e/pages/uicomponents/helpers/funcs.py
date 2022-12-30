def format_xpath_from_parent(xpath: str):
    """
    Returns xpath relative to the parent
    :param xpath:
    :return:
    """
    if xpath.startswith("//"):
        xpath = xpath.replace("//", "/", 1)
    return f"./{xpath}"
