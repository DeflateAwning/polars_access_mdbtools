"""Tests for reading tables from Access databases."""

from pathlib import Path

import pytest

from polars_access_mdbtools import read_table


def test_can_read_all_tables_in_sample_db_1(sample_db_1: Path) -> None:
    """Test reading all tables in sample_db_1. Check row counts."""
    for table_name, expected_rows in [
        ("CMD_LINE_TB", 14),
        ("CUM_VAL_TB", 59),
        ("DATABASE_STRUCTURE_TB", 46),
        ("DECUM_VAL_TB", 59),
        ("ROULETTE_TB", 38),
        ("TAG_GRP_TB", 19),
        ("TAG_NME_TB", 933),
        ("tblContacts", 0),
        ("tblDefaults", 1),
        ("tblFileList", 0),
        ("USysRibbons", 2),
    ]:
        df = read_table(sample_db_1, table_name)
        assert df.height == expected_rows, (
            f"Table {table_name} should have {expected_rows} rows, but had {df.height}."
        )


def test_read_nonexistent_table_raises_value_error(sample_db_1: Path) -> None:
    """Test that reading a nonexistent table raises ValueError."""
    nonexistent_table_name = "NONEXISTENT_TABLE"
    with pytest.raises(
        ValueError,
        match=f'Table "{nonexistent_table_name}" not found in database',
    ):
        read_table(sample_db_1, nonexistent_table_name)
