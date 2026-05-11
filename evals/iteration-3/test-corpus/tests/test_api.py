import time
from inventory.api import search


def test_search_returns_list():
    result = search("widget")
    time.sleep(1)
    assert isinstance(result, list)
