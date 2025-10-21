"""Test the `list_table_names()` function."""

from pathlib import Path

import pytest

from polars_access_mdbtools import list_table_names


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_list_table_names_db_1(sample_db_1: Path) -> None:
    table_names = list_table_names(sample_db_1)
    assert isinstance(table_names, list)
    assert table_names == [
        "CMD_LINE_TB",
        "CUM_VAL_TB",
        "DATABASE_STRUCTURE_TB",
        "DECUM_VAL_TB",
        "ROULETTE_TB",
        "TAG_GRP_TB",
        "TAG_NME_TB",
        "tblContacts",
        "tblDefaults",
        "tblFileList",
        "USysRibbons",
    ]


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_list_table_names_db_2(sample_db_2: Path) -> None:
    table_names = list_table_names(sample_db_2)
    assert isinstance(table_names, list)
    assert table_names == [
        "Colors",
        "Colors Table Two",
        "Colors-Table Others",
        "Dictionary",
        "Users",
        "Colors 1°à",
    ]
