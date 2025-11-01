from abc import ABC
from typing import Generic, TypeVar
import json
from pathlib import Path

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _read_json(self, filename: str) -> dict:
        filepath = self.data_dir / filename
        if filepath.exists():
            with open(filepath) as f:
                return json.load(f)
        return {}

    def _write_json(self, filename: str, data: dict) -> None:
        filepath = self.data_dir / filename
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
