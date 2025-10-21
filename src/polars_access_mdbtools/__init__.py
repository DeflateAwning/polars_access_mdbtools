"""Read tables from an Access database into Polars dataframes, using mdbtools."""

import io
import locale
import os
import re
import subprocess
import warnings
from collections.abc import Sequence
from pathlib import Path

import polars as pl
from polars._typing import PolarsDataType

CREATE_TABLE_RE = re.compile(
    r"CREATE TABLE \[([^]]+)\]\s+\((.*?\));",
    re.MULTILINE | re.DOTALL,
)

DATA_TYPE_DEF_RE = re.compile(
    r"^\s*\[(?P<column_name>[^\]]+)\]\s*(?P<data_type>[A-Za-z]+[^,]+),?",
)


def _path_to_cmd_str(input_path: str | Path) -> str:
    """Convert a Path to a command-line string, quoting as needed.

    :param input_path: The input path.
    :return: A command-line safe string.
    """
    input_path = Path(input_path)
    return str(input_path.resolve())


def list_table_names(db_path: str | Path) -> list[str]:
    """List the names of the tables in a given database using 'mdb-tables'.

    :param db_path: The MS Access database file.
    :return: A list of the tables in a given database.
    """
    tables = (
        subprocess.check_output(  # noqa: S603
            ["mdb-tables", "--single-column", _path_to_cmd_str(db_path)],  # noqa: S607
        )
        .decode(locale.getpreferredencoding())
        .replace("\r\n", "\n")
        .strip()
    )
    return tables.split("\n")


def _convert_data_type_from_access_to_polars(  # noqa: C901, PLR0911, PLR0912
    data_type: str,
) -> PolarsDataType | None:
    # Source: https://github.com/mdbtools/mdbtools/blob/0e77b68e76701ddc7aacb2c2e10ecdad1bb530ec/src/libmdb/backend.c#L27
    data_type = data_type.lower().strip()
    if data_type.startswith("boolean"):
        return pl.Boolean
    if data_type.startswith("byte"):
        return pl.UInt8
    if data_type.startswith("integer"):
        return pl.Int32
    if data_type.startswith("long integer"):
        return pl.Int64
    if data_type.startswith("currency"):
        return pl.Decimal
    if data_type.startswith("single"):
        return pl.Float32
    if data_type.startswith("double"):
        return pl.Float64
    if data_type.startswith("datetime"):
        return pl.Datetime
    if data_type.startswith("binary"):
        return pl.Binary
    if data_type.startswith("text"):
        return pl.String
    if data_type.startswith("ole"):
        return pl.String  # Maybe there's a better option.
    if "integer" in data_type:
        # This shouldn't happen, as 'integer' and 'long integer' are already handled.
        return pl.Int32
    if data_type.startswith("memo"):  # 'memo/hyperlink'
        return pl.String
    if data_type.startswith("hyperlink"):
        # Might not be real.
        return pl.String
    if data_type.startswith("replication id"):
        return pl.String
    if data_type.startswith("date"):
        # Might not be real.
        return pl.Date
    return None


def _extract_data_type_definitions(defs_str: str) -> dict[str, str]:
    defs: dict[str, str] = {}
    lines = defs_str.splitlines()
    for line in lines:
        type_def_match = DATA_TYPE_DEF_RE.match(line)
        if type_def_match:
            column_name = type_def_match.group("column_name")
            data_type = type_def_match.group("data_type")
            defs[column_name] = data_type
    return defs


def _read_table_mdb_schema(
    db_path: str | Path,
    table_name: str,
) -> dict[str, str]:
    """Read the schema of a given database into a dictionary of the mdb-schema output.

    :param db_path: The MS Access database file.
    :return: a dictionary of `{column_name: access_data_type}`
    """
    cmd = [
        "mdb-schema",
        # TODO(DeflateAwning): Could add these as arguments.
        "--no-default-values",
        "--no-not_empty",
        "--no-comments",
        "--no-indexes",
        "--no-relations",
        "--table",
        table_name,
        str(db_path),
    ]
    try:
        cmd_output = subprocess.check_output(cmd, stderr=subprocess.STDOUT)  # noqa: S603
    except subprocess.CalledProcessError as e:
        # Remap "table not found" problem.
        if b"No table named" in e.output:
            msg = f'Table "{table_name}" not found in database.'
            raise ValueError(msg) from e
        raise

    cmd_output = cmd_output.decode(locale.getpreferredencoding())
    lines = cmd_output.splitlines()
    schema_ddl = "\n".join(line for line in lines if line and not line.startswith("-"))

    create_table_matches = CREATE_TABLE_RE.findall(schema_ddl)

    # These failures are likely more related to implementation issues, and less
    # about the table being missing.
    if len(create_table_matches) == 0:
        msg = f'Table schema "{table_name}" not found in "mdb-schema" output.'
        raise ValueError(msg)
    if len(create_table_matches) > 1:
        msg = (
            f'Multiple table schemas found for "{table_name}" in "mdb-schema" output. '
            "Logical error."
        )
        raise ValueError(msg)

    table_name_mdb, defs = create_table_matches[0]
    if table_name_mdb != table_name:
        msg = (
            f'Table name mismatch from "mdb-schema" response: '
            f"table_name_arg={table_name}, {table_name_mdb=}"
        )
        raise ValueError(msg)

    return _extract_data_type_definitions(defs)


def _convert_mdb_schema_to_polars_schema(
    mdb_schema: dict[str, str],
    *,
    implicit_string: bool = True,
) -> dict[str, PolarsDataType]:
    """Convert a table's schema format to Polars schema format.

    :param schema: the output of `_read_table_mdb_schema(...)`
    :param implicit_string: If True, mark strings and unknown datatypes as `pl.String`.
        Otherwise, raise an error on unhandled SQL data types.
    :return: a dictionary of `{column_name: pl.DataType}`
    """
    pl_table_schema: dict[str, PolarsDataType] = {}
    for column, data_type in mdb_schema.items():
        pl_data_type = _convert_data_type_from_access_to_polars(data_type)
        if pl_data_type is not None:
            pl_table_schema[column] = pl_data_type
        elif implicit_string is True:
            pl_table_schema[column] = pl.String
        else:
            msg = f"Unhandled data type: {column=}, {data_type=}"
            raise ValueError(msg)
    return pl_table_schema


def read_table(
    db_path: str | Path,
    table_name: str,
    *,
    implicit_string: bool = True,
    null_values: Sequence[str] = (),
) -> pl.DataFrame:
    """Read a MS Access database as a Polars DataFrame.

    :param db_path: The MS Access database file.
    :param table_name: The name of the table to process.
    :param implicit_string: If True, mark strings and unknown datatypes as `pl.String`.
        Otherwise, raise an error on unhandled SQL data types.
    :param null_values: Additional string values to treat as nulls.
    :return: a `pl.DataFrame`
    """
    mdb_schema = _read_table_mdb_schema(db_path, table_name)
    pl_schema_target = _convert_mdb_schema_to_polars_schema(
        mdb_schema,
        implicit_string=implicit_string,
    )

    # Transform the schema from target types to temporary types to read in the CSV.
    pl_schema_read: dict[str, PolarsDataType] = {}
    boolean_col_names: list[str] = []
    binary_col_names: list[str] = []
    for col_name, col_type in pl_schema_target.items():
        if col_type == pl.Binary:
            # Must read as string (hex), then convert to binary.
            pl_schema_read[col_name] = pl.String
            binary_col_names.append(col_name)
        elif col_type == pl.Boolean:
            # Must read as UInt8 (0, 1, NULL), then convert to pl.Boolean after.
            pl_schema_read[col_name] = pl.UInt8
            boolean_col_names.append(col_name)
        else:
            pl_schema_read[col_name] = col_type

    cmd = [
        "mdb-export",
        "--bin=hex",
        "--date-format",
        "%Y-%m-%d",
        "--datetime-format",
        "%Y-%m-%dT%H:%M:%S",
        _path_to_cmd_str(db_path),
        table_name,
    ]

    with subprocess.Popen(cmd, stdout=subprocess.PIPE) as proc:  # noqa: S603
        if proc.stdout is None:
            msg = "Failed to read from mdb-export subprocess stdout."
            raise RuntimeError(msg)

        if locale.getpreferredencoding().lower() in {"utf-8", "utf8"}:
            csv_io = proc.stdout
        else:
            incoming_bytes = proc.stdout.read()
            incoming_str = incoming_bytes.decode(locale.getpreferredencoding())
            csv_re_encoded = incoming_str.encode("utf-8")

            # If on Windows, replace CRLF with LF.
            if os.name == "nt":
                csv_re_encoded = csv_re_encoded.replace(b"\r\n", b"\n")

            csv_io = io.BytesIO(csv_re_encoded)

        # Silence this warning:
        # UserWarning: Polars found a filename.
        # Ensure you pass a path to the file instead of a python file object when
        # possible for best performance.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="Polars found a filename.*")

            df = pl.read_csv(
                csv_io,
                schema=pl_schema_read,
                null_values=[
                    "1900-01-00T00:00:00",  # Insane datetime value.
                    "1900-01-00",  # Insane date value.
                    *null_values,
                ],
            )

    # Convert binary columns to hex.
    df = df.with_columns(
        pl.col(col_name).str.decode("hex") for col_name in binary_col_names
    )

    # Convert boolean columns.
    return df.with_columns(
        (pl.col(col_name) > pl.lit(0)).cast(pl.Boolean).alias(col_name)
        for col_name in boolean_col_names
    )
