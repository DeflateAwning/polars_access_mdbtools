"""Test to ensure mdbtools is installed and accessible."""

import subprocess

import pytest


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_mdbtools_installed() -> None:
    """Test that mdbtools commands are accessible."""
    try:
        result = subprocess.run(
            ["mdb-ver", "--version"],  # noqa: S607
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()
        assert "mdbtools" in output, (
            "mdb-ver output does not indicate MDB Tools is installed."
        )
    except FileNotFoundError:
        pytest.fail("mdb-ver command not found. MDB Tools may not be installed.")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"mdb-ver command failed with error: {e.stderr.strip()}")
