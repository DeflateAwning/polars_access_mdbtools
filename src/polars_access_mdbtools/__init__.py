import re
import subprocess
from typing import Union
import os
import warnings

import polars as pl


CREATE_TABLE_RE = re.compile("CREATE TABLE \[([^]]+)\]\s+\((.*?\));",
                      re.MULTILINE | re.DOTALL)

DATA_TYPE_DEF_RE = re.compile(r"^\s*\[(?P<column_name>[^\]]+)\]\s*(?P<data_type>[A-Za-z]+[^,]+),?")

def list_table_names(rdb_file: Union[str, os.PathLike], encoding: str = 'utf-8') -> list[str]:
    """
    Lists the names of the tables in a given database using 'mdb-tables'.

    :param rdb_file: The MS Access database file.
    :param encoding: The content encoding of the output of the mdb-tables command.
    :return: A list of the tables in a given database.
    """
    tables = subprocess.check_output(['mdb-tables', "--single-column", rdb_file]).decode(encoding)
    return tables.strip().split("\n")


def _convert_data_type_from_access_to_polars(data_type: str) -> Union[pl.DataType, None]:
    # Source: https://github.com/mdbtools/mdbtools/blob/0e77b68e76701ddc7aacb2c2e10ecdad1bb530ec/src/libmdb/backend.c#L27
    data_type = data_type.lower().strip()
    if data_type.startswith('boolean'):
        return pl.Boolean
    elif data_type.startswith('byte'):
        return pl.UInt8
    elif data_type.startswith('integer'):
        return pl.Int32
    elif data_type.startswith('long integer'):
        return pl.Int64
    elif data_type.startswith('currency'):
        return pl.Decimal
    elif data_type.startswith('single'):
        return pl.Float32
    elif data_type.startswith('double'):
        return pl.Float64
    elif data_type.startswith('datetime'):
        return pl.Datetime
    elif data_type.startswith('binary'):
        return pl.Binary
    elif data_type.startswith('text'):
        return pl.String
    elif data_type.startswith('ole'):
        return pl.String # maybe there's a better option
    elif "integer" in data_type:
        # this shouldn't happen, as both 'integer' and 'long integer' are already handled
        return pl.Int32
    elif data_type.startswith('memo'): # 'memo/hyperlink'
        return pl.String
    elif data_type.startswith('hyperlink'):
        # Might not be real
        return pl.String
    elif data_type.startswith('replication id'):
        return pl.String
    elif data_type.startswith('date'):
        # Might not be real
        return pl.Date
    #raise ValueError(f"Unknown data type: {data_type}")
    return None

def _extract_data_type_definitions(defs_str: str) -> dict[str, str]:
    defs = {}
    lines = defs_str.splitlines()
    for line in lines:
        type_def_match = DATA_TYPE_DEF_RE.match(line)
        if type_def_match:
            column_name = type_def_match.group('column_name')
            data_type = type_def_match.group('data_type')
            defs[column_name] = data_type
    return defs

def _read_table_mdb_schema(rdb_file: Union[str, os.PathLike], table_name: str, encoding: str = 'utf-8') -> dict[str, str]:
    """
    Reads the schema of a given database using 'mdb-schema', and returns it in a dictionary representation of the mdb-schema output.

    :param rdb_file: The MS Access database file.
    :param encoding: The schema encoding.
    :return: a dictionary of `{column_name: access_data_type}`
    """
    cmd = [
        'mdb-schema',
        '--no-default-values', # TODO: could add these as arguments in case anyone ever wants to use them
        '--no-not_empty',
        '--no-comments',
        '--no-indexes',
        '--no-relations',
        '--table', table_name,
        rdb_file]
    cmd_output = subprocess.check_output(cmd)
    cmd_output = cmd_output.decode(encoding)
    lines = cmd_output.splitlines()
    schema_ddl = "\n".join(l for l in lines if l and not l.startswith('-'))

    create_table_matches = CREATE_TABLE_RE.findall(schema_ddl)
    if len(create_table_matches) == 0:
        raise ValueError(f"Table schema {table_name} not found in 'mdb-schema' output.")
    if len(create_table_matches) > 1:
        # TODO: could be a warning
        raise ValueError(f"Multiple table schemas found for {table_name} in 'mdb-schema' output.")
    
    table_name_mdb, defs = create_table_matches[0]
    if table_name_mdb != table_name:
        raise ValueError(f"Table name mismatch from 'mdb-schema' response: table_name_arg={table_name}, {table_name_mdb=}")
    
    pl_schema = _extract_data_type_definitions(defs)
    return pl_schema


def _convert_mdb_schema_to_polars_schema(mdb_schema: dict[str, pl.DataType], implicit_string: bool = True) -> dict[str, pl.DataType]:
    """
    Converts a table's schema from `_read_table_mdb_schema(...)` format to Polars schema format.

    :param schema: the output of `read_schema`
    :param implicit_string: If true, mark strings and unknown datatypes as `pl.String`. Otherwise, raise an error on unhandled SQL data types.
    :return: a dictionary of `{column_name: pl.DataType}`
    """

    pl_table_schema: dict[str, pl.DataType] = {}
    for column, data_type in mdb_schema.items():
        pl_data_type = _convert_data_type_from_access_to_polars(data_type)
        if pl_data_type is not None:
            pl_table_schema[column] = pl_data_type
        elif implicit_string:
            pl_table_schema[column] = pl.String
        else:
            raise ValueError(f"Unhandled data type: {column=}, {data_type=}")
    return pl_table_schema


def read_table(rdb_file: Union[str, os.PathLike], table_name: str, data_encoding: str = 'utf-8', implicit_string: bool = True) -> pl.DataFrame:
    """
    Read a MS Access database as a Polars DataFrame.

    :param rdb_file: The MS Access database file.
    :param table_name: The name of the table to process.
    :param implicit_string: If true, mark strings and unknown datatypes as `pl.String`. Otherwise, raise an error on unhandled SQL data types.
    :return: a `pl.DataFrame`
    """
    schema_encoding = 'utf-8'
    mdb_schema = _read_table_mdb_schema(rdb_file, table_name, schema_encoding)
    pl_schema_target = _convert_mdb_schema_to_polars_schema(mdb_schema, implicit_string)
    
    # transform the schema to a format that Polars can read (pl_schema_target -> pl_schema_read)
    pl_schema_read: dict[str, pl.DataType] = {}
    boolean_col_names: list[str] = []
    binary_col_names: list[str] = []
    for col_name, col_type in pl_schema_target.items():
        if col_type == pl.Binary:
            # must read as string (hex), then convert to binary
            pl_schema_read[col_name] = pl.String
            binary_col_names.append(col_name)
        elif col_type == pl.Boolean:
            # must read as UInt8 (0, 1, NULL), then convert to pl.Boolean after
            pl_schema_read[col_name] = pl.UInt8
            boolean_col_names.append(col_name)
        else:
            pl_schema_read[col_name] = col_type

    cmd = ['mdb-export', '--bin=hex', '--date-format', '%Y-%m-%d', '--datetime-format', '%Y-%m-%dT%H:%M:%S', rdb_file, table_name]
    
    # Debug:
    # data_str = subprocess.check_output(cmd).decode(data_encoding)
    # with open('test.csv', 'w') as f:
    #     f.write(data_str)
    
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    # silence this warning: UserWarning: Polars found a filename. Ensure you pass a path to the file instead of a python file object when possible for best performance

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Polars found a filename.*")
        
        df = pl.read_csv(
            proc.stdout,
            schema=pl_schema_read,
            encoding=data_encoding,
            # truncate_ragged_lines=True,
        )

    # convert binary columns
    df = df.with_columns([
        pl.col(col_name).str.decode('hex')
        for col_name in binary_col_names
    ])

    # convert boolean columns
    df = df.with_columns([
        (pl.col(col_name) > pl.lit(0)).cast(pl.Boolean).alias(col_name)
        for col_name in boolean_col_names
    ])

    return df
