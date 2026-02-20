from pathlib import Path
from typing import Protocol


class ExistingFileValidator(Protocol):
    def is_existing_file(self, file_path: Path) -> bool: ...


class LocalStorageExistingFileValidator:
    def __init__(self, base_directory: Path) -> None:
        if not base_directory.exists():
            raise Exception("Address provided does not exist")

        if not base_directory.is_dir():
            raise Exception("Address provided is not a directory")

        self._base_directory = base_directory
        self._contained_files = {str(child) for child in self._base_directory.iterdir()}

    def _update_existing_files_(self) -> set[str]:
        return {str(child) for child in self._base_directory.iterdir()}

    def is_existing_file(self, file_path: Path) -> bool:
        self._contained_files = self._update_existing_files_()
        return str(file_path) in self._contained_files
