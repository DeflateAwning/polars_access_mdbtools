"""Tests for reading tables from Access databases."""

from pathlib import Path

import polars as pl
import pytest
from polars.testing import assert_frame_equal

from polars_access_mdbtools import read_table


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
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


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_read_nonexistent_table_raises_value_error(sample_db_1: Path) -> None:
    """Test that reading a nonexistent table raises ValueError."""
    nonexistent_table_name = "NONEXISTENT_TABLE"
    with pytest.raises(
        ValueError,
        match=f'Table "{nonexistent_table_name}" not found in database',
    ):
        read_table(sample_db_1, nonexistent_table_name)


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_reading_specific_table_1a(sample_db_1: Path) -> None:
    """Test reading a specific table and checking its schema."""
    df = read_table(sample_db_1, table_name="USysRibbons")

    df_expected = pl.DataFrame(
        {
            "RibbonId": [1, 6],
            "RibbonName": ["rbnReportView", "rbnMainMenu"],
            "RibbonXML": [
                '<customUI xmlns="http://schemas.microsoft.com/office/2006/01/customui">\r\n <ribbon startFromScratch="true">\r\n  <officeMenu>\r\n   <button idMso="FileCompactAndRepairDatabase" insertBeforeMso ="FileCloseDatabase" />\r\n   <button idMso="FileOpenDatabase" visible="false"/>\r\n   <button idMso="FileNewDatabase" visible="false"/>\r\n   <splitButton idMso="FileSaveAsMenuAccess" visible="false" />\r\n  </officeMenu>\r\n  <tabs>\r\n    <tab id="tabHome" label="Home">\r\n\r\n       <group id="grpClose" label="Close" >\r\n          <button idMso="PrintPreviewClose" \r\n             size="large" />\r\n       </group>\r\n\r\n       <group id="grpData" label="Data" >\r\n          <button idMso="PublishToPdfOrEdoc"\r\n             size="large" />\r\n       </group>\r\n\r\n       <group id="grpZoom" label="Zoom" >\r\n          <splitButton idMso="PrintPreviewZoomMenu"\r\n             size="large" />\r\n       </group>\r\n\r\n       <group id="grpPrint" label="Print" >\r\n          <button idMso="PrintDialogAccess"\r\n             size="large" />\r\n       </group>\r\n\r\n    </tab>\r\n  </tabs>\r\n </ribbon>\r\n</customUI>',  # noqa: E501
                '<customUI xmlns="http://schemas.microsoft.com/office/2006/01/customui">\r\n <ribbon startFromScratch="true">\r\n  <officeMenu>\r\n   <button idMso="FileCompactAndRepairDatabase" insertBeforeMso ="FileCloseDatabase" />\r\n   <button idMso="FileOpenDatabase" visible="false"/>\r\n   <button idMso="FileNewDatabase" visible="false"/>\r\n   <splitButton idMso="FileSaveAsMenuAccess" visible="false" />\r\n  </officeMenu>\r\n  <tabs>\r\n   <tab id="tabHome" label="Home">\r\n\r\n       <group id="grpClose" label="Close" >\r\n          <button idMso="FileExit"\r\n              label="Exit Database" \r\n              imageMso="MasterViewClose" \r\n              size="large" />\r\n       </group>\r\n\r\n       <group id="grpSort" label="Sort" >\r\n           <button idMso="SortUp"\r\n              size="large"/>\r\n\r\n            <button idMso="SortDown"\r\n              size="large"/>\r\n\r\n            <button idMso="SortRemoveAllSorts" \r\n               size="large" />\r\n       </group>\r\n\r\n       <group id="grpFilter" label="Filter" >\r\n          <toggleButton idMso="FilterMenu"  \r\n              size="large"/>\r\n\r\n          <button idMso="FilterClearAllFilters"  \r\n              size="large"/>\r\n       </group>\r\n\r\n       <group id="grpReport" label="Reports" >\r\n          <button id="cmdViewReport" \r\n             label="View Detail Report" \r\n            size="large" \r\n            imageMso="ViewsReportView" \r\n            onAction="Ribbon.OpenDetailReport"/>\r\n       </group>\r\n   </tab>\r\n\r\n   <tab id="tabSystem" label="System">\r\n       <group id="grpTables" label="Database Tools" >\r\n            <button idMso="DatabaseLinedTableManager"\r\n               size="large" />\r\n\r\n            <button idMso="FileDatabaseProperties"\r\n               size="large" />\r\n       </group>\r\n\r\n       <group id="grpInfo" label="Information" >\r\n            <button id="cmdOpenAbout"\r\n               label="About" \r\n               size="large" \r\n               imageMso="CreateFormBlankForm" \r\n              onAction="Ribbon.OpenAboutForm"/>\r\n       </group>\r\n   </tab>\r\n\r\n  </tabs>\r\n </ribbon>\r\n</customUI>',  # noqa: E501
            ],
            "RibbonNotes": [None, None],
        },
        schema={
            "RibbonId": pl.Int64,
            "RibbonName": pl.String,
            "RibbonXML": pl.String,
            "RibbonNotes": pl.String,
        },
    )
    assert_frame_equal(df, df_expected)


@pytest.mark.filterwarnings("error")  # Make sure no warnings are raised.
def test_reading_specific_table_2a(sample_db_2: Path) -> None:
    """Test reading a specific table and checking its schema.

    Table contains string columns with non-ASCII characters.
    """
    df = read_table(sample_db_2, table_name="Colors-Table Others")

    df_expected = pl.DataFrame(
        [
            {"Colors": "Red", "Value": 10, "Second Value": 5, "Others-A": "à"},
            {"Colors": "Green", "Value": 5, "Second Value": 3, "Others-A": "1a"},
            {"Colors": "Blue", "Value": 16, "Second Value": 4, "Others-A": "ò"},
            {"Colors": "Black", "Value": 1, "Second Value": 3, "Others-A": "2°"},
            {"Colors": "Yellow", "Value": 12, "Second Value": 3, "Others-A": "Y"},
            {"Colors": "White", "Value": 10, "Second Value": 1, "Others-A": "W"},
            {"Colors": "Others", "Value": 0, "Second Value": 0, "Others-A": "A"},
        ],
        schema={
            "Colors": pl.String,
            "Value": pl.Int64,
            "Second Value": pl.Int64,
            "Others-A": pl.String,
        },
    )
    assert_frame_equal(df, df_expected)
