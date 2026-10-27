"""Test utils module"""

from custom_components.openwisp import utils


def test_get_and_apply():
    assert utils.get_and_apply({"foo": "bar"}, "foo", str.upper) == "BAR"
    assert utils.get_and_apply({"foo": "bar"}, "baz", str.upper) is None
    assert utils.get_and_apply({"foo": "bar"}, "baz", str.upper, default="BAZ") == "BAZ"
