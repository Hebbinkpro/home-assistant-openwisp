from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Callable, TypeVar

    T = TypeVar("T")
    R = TypeVar("R")


def get_and_apply(data: dict, key: str, func: Callable[[T], R], default: R | None = None) -> R | None:
    """
    Get a value from a dictionary and call a function on it when it exists, otherwise return default.
    """
    v = data.get(key)
    if v is not None:
        return func(v)

    return default