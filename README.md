# polars_access_mdbtools
A library for reading tables from an Access database into Polars dataframes, using mdbtools

## What is this?

A tiny, `subprocess`-based tool for reading a 
[MS Access](https://products.office.com/en-us/access) 
database (`.mdb`, `.accdb`, `.rdb`) as a [Python Polars Dataframe](https://docs.pola.rs).

## Installation

To read the database, this package thinly wraps 
[MDBTools](https://github.com/mdbtools/mdbtools).

If you are on `macOS`, install it via [Homebrew](http://brew.sh/):

```sh
$ brew install mdbtools
```

If you are on `Debian`, install it via apt:
```sh
$ sudo apt install mdbtools
```

If you are on `Windows`, it's a little tougher. Install `mdbtools` for [Windows](https://github.com/lsgunth/mdbtools-win). Manually add to PATH.
1. Download the mdb-tools files from Windows link above. Visit the Releases section, then download the part that says "Source Code (zip)".
2. Extract that to somewhere like `C:/bin/mdbtools-win/mdbtools-win-1.0.0`.
3. Follow these instructions to [add that folder to your environment path](https://linuxhint.com/add-directory-to-path-environment-variables-windows/) (Method 1, but use the path to the mdbtools executable files).
4. Restart your computer or just close and re-open the program you're running it from. You can test that it works by opening a terminal and running `mdb-tables --help` and see that it doesn't fail.

Finally, on all OS's:
```sh
$ pip install polars_access_mdbtools
```

## Example Usage

```python
import polars as pl
import polars_access_mdbtools as pl_access

file_path = "path_to_file.mdb"
print(pl_access.list_table_names(file_path))

df: pl.DataFrame = pl_access.read_table(file_path, table_name="your_table_name")
```

## Acknowledgements

This code is based heavily on [jbn's `pandas_access` library](https://github.com/jbn/pandas_access).

## Contributing

Please Star this repo. 

Please submit bug reports as GitHub Issues. Feel free to submit a PR to fix an issue!

