"""Project logger with a transparent fallback when loguru is unavailable."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


class _FallbackLogger:
    def __init__(self) -> None:
        self._logger = logging.getLogger("project_data_science")
        if not self._logger.handlers:
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(
                logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
            )
            self._logger.addHandler(stream_handler)
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False
        self._file_sinks: set[str] = set()

    def add(self, sink: str | Path, rotation: str | None = None, **_: Any) -> str:
        del rotation
        path = Path(sink)
        path.parent.mkdir(parents=True, exist_ok=True)
        resolved = str(path.resolve())
        if resolved in self._file_sinks:
            return resolved

        file_handler = logging.FileHandler(path, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        )
        self._logger.addHandler(file_handler)
        self._file_sinks.add(resolved)
        return resolved

    def debug(self, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(*args, **kwargs)

    def info(self, *args: Any, **kwargs: Any) -> None:
        self._logger.info(*args, **kwargs)

    def warning(self, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(*args, **kwargs)

    def error(self, *args: Any, **kwargs: Any) -> None:
        self._logger.error(*args, **kwargs)

    def exception(self, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(*args, **kwargs)

    def success(self, *args: Any, **kwargs: Any) -> None:
        self._logger.info(*args, **kwargs)


try:
    from loguru import logger as _loguru_logger
except ModuleNotFoundError:
    logger = _FallbackLogger()
else:
    logger = _loguru_logger
