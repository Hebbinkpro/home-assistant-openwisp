import pytest

import custom_components.openwisp.utils as utils

def test_get_and_apply():
    assert utils.get_and_apply({"foo": "bar"}, "foo", str.upper) == "BAR"
    assert utils.get_and_apply({"foo": "bar"}, "baz", str.upper) is None
    assert utils.get_and_apply({"foo": "bar"}, "baz", str.upper, default="BAZ") == "BAZ"

