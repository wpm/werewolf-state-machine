import sys
from enum import StrEnum
from typing import Self

from loguru import logger

__version__ = "0.1.0"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


def initialize_logger(log_level: LogLevel) -> None:
    logger.remove()
    logger.add(sys.stderr, level=log_level.upper(), colorize=True)


class Hashable:
    """
    Make objects hashable.

    Custom logic must be written for objects that contain mutable members other than lists and dictionaries.
    """

    @property
    def _signature(self):
        def unique_and_immutable(obj):
            match obj:
                case dict():
                    return tuple(
                        sorted((k, unique_and_immutable(v)) for k, v in obj.items())
                    )
                case list():
                    return tuple(unique_and_immutable(v) for v in obj)
                case set():
                    return tuple(
                        unique_and_immutable(v)
                        for v in sorted(obj, key=lambda v: str(v))
                    )
                case _:
                    return obj

        return unique_and_immutable(self.__dict__)

    def __eq__(self, other: Self) -> bool:
        return self._signature == other._signature

    def __hash__(self):
        return hash(self._signature)
