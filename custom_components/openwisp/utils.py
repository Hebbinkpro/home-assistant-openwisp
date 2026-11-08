"""Utility functions."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeVar, Any

    T = TypeVar("T")
    R = TypeVar("R")


def get_and_apply[T, R](
    data: dict, key: str, func: Callable[[T], R], default: R | None = None
) -> R | None:
    """
    Get a value from a dictionary and call a function on it when it exists.

    :returns the result of the function call or default if the key is not found
    """
    v = data.get(key)
    if v is not None:
        return func(v)

    return default

def parse_bool(value: Any) -> bool | None:
    """Normalize inconsistent API boolean values."""
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        value = value.strip().lower()

        if value in ("true", "1", "yes", "on"):
            return True

        if value in ("false", "0", "no", "off"):
            return False

    return None