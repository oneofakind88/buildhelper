from __future__ import annotations

from abc import ABC
from functools import wraps
from typing import Any, Callable, Mapping, ParamSpec, TypeVar


P = ParamSpec("P")
T = TypeVar("T")


class BaseBackend(ABC):
    """Base class for all backend implementations."""

    def __init__(self, name: str, config: Mapping[str, Any] | None = None, env: str | None = None) -> None:
        self.name = name
        self.config = dict(config or {})
        self.env = env
        self._connected = False

    def connect(self) -> None:
        """Establish a connection to the backend.

        Subclasses may override this method to perform setup such as
        authentication or network handshakes. The default implementation is a
        no-op to keep simple backends lightweight.
        """

        self._connected = True
        return None


def require_connection(method: Callable[P, T]) -> Callable[P, T]:
    """Ensure the backend is connected before invoking ``method``.

    The decorator reuses the existing connection on the instance when
    available, otherwise it initializes it by calling ``connect``.
    """

    @wraps(method)
    def wrapper(self: BaseBackend, *args: P.args, **kwargs: P.kwargs) -> T:
        if not getattr(self, "_connected", False):
            self.connect()
            self._connected = True

        return method(self, *args, **kwargs)

    return wrapper
