"""Fixtures (sample files) for tests."""

import hashlib
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest
import requests


def _sha256_checksum(file_path: Path) -> str:
    """Compute the SHA-256 checksum of a file.

    :param file_path: The path to the file.
    :return: The SHA-256 checksum as a hexadecimal string.
    """
    sha256 = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


@pytest.fixture
def sample_db_1() -> Iterator[Path]:
    """Give a sample access database file for tests.

    Download the Access Example .accdb file to a temporary directory,
    yield its path for tests, and delete it afterward.
    """
    url = "https://github.com/Access-projects/Access-examples/raw/refs/heads/master/Access_Example_VBA.accdb"
    with tempfile.TemporaryDirectory() as temp_dir_str:
        db_path = Path(temp_dir_str) / "Access_Example_VBA.accdb"
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        db_path.write_bytes(response.content)
        assert (
            _sha256_checksum(db_path)
            == "3cd1fc88d70bc93909ae6d190fa9692e709d5641b205fd2f66185c905e42cfbf"
        ), "Downloaded file checksum does not match expected value."

        yield db_path  # Provide file path to test.
        # Tempdir automatically cleaned up on exit.


@pytest.fixture
def sample_db_2() -> Iterator[Path]:
    """Give another sample access database file for tests.

    Download the Access Sample .mdb file to a temporary directory,
    yield its path for tests, and delete it afterward.
    """
    url = "https://github.com/el3um4s/mdbtools/raw/refs/heads/main/src/__tests__/test%202.mdb"
    with tempfile.TemporaryDirectory() as temp_dir_str:
        db_path = Path(temp_dir_str) / "file_example_MDB_250kB.mdb"
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        db_path.write_bytes(response.content)
        assert (
            _sha256_checksum(db_path)
            == "560bfd44ad5a6efbab4c86622c92a7071eda9d73c3b453e4bba227d82d725fec"
        ), "Downloaded file checksum does not match expected value."

        yield db_path  # Provide file path to test.
        # Tempdir automatically cleaned up on exit.
