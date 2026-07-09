from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd


def normalize_table_name(value: str) -> str:
    value = Path(value).stem
    value = re.sub(r"[^0-9a-zA-Z_]+", "_", value)
    value = re.sub(r"_+", "_", value).strip("_").lower()
    return value or "data"


def read_csv_with_optional_dates(path: Path, date_columns: list[str] | None) -> pd.DataFrame:
    if date_columns:
        return pd.read_csv(path, parse_dates=date_columns)
    return pd.read_csv(path)


def coerce_for_sqlite(df: pd.DataFrame) -> pd.DataFrame:
    frame = df.copy()

    for column in frame.columns:
        series = frame[column]

        if pd.api.types.is_bool_dtype(series):
            frame[column] = series.astype("Int64")
            continue

        if pd.api.types.is_datetime64_any_dtype(series):
            frame[column] = series.dt.strftime("%Y-%m-%d %H:%M:%S")
            continue

        if pd.api.types.is_timedelta64_dtype(series):
            frame[column] = series.astype("string")

    return frame


def infer_sqlite_type(series: pd.Series) -> str:
    if pd.api.types.is_integer_dtype(series):
        return "INTEGER"
    if pd.api.types.is_float_dtype(series):
        return "REAL"
    if pd.api.types.is_bool_dtype(series):
        return "INTEGER"
    return "TEXT"


def build_create_table_sql(df: pd.DataFrame, table_name: str) -> str:
    columns = []
    for column in df.columns:
        sql_type = infer_sqlite_type(df[column])
        safe_name = column.replace('"', '""')
        columns.append(f'"{safe_name}" {sql_type}')
    columns_sql = ",\n    ".join(columns)
    return f'CREATE TABLE IF NOT EXISTS "{table_name}" (\n    {columns_sql}\n);'


def write_sqlite_table(
    csv_path: Path,
    sqlite_path: Path,
    table_name: str,
    date_columns: list[str] | None,
    if_exists: str,
) -> None:
    df = read_csv_with_optional_dates(csv_path, date_columns)
    df = coerce_for_sqlite(df)

    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(sqlite_path) as connection:
        existing = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()

        if existing and if_exists == "fail":
            raise ValueError(f'table "{table_name}" already exists in {sqlite_path}')

        if if_exists == "replace":
            connection.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        connection.execute(build_create_table_sql(df, table_name))
        df.to_sql(table_name, connection, if_exists="append", index=False)
        connection.commit()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a CSV file to a SQLite database.")
    parser.add_argument("csv_path", type=Path, help="Input CSV file.")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output SQLite database path. Defaults to the CSV stem with .db in the same folder.",
    )
    parser.add_argument(
        "-t",
        "--table",
        default=None,
        help="Table name to create. Defaults to a normalized version of the CSV stem.",
    )
    parser.add_argument(
        "--date-column",
        action="append",
        default=None,
        help="Column to parse as a date. Use multiple times for multiple columns.",
    )
    parser.add_argument(
        "--if-exists",
        choices=["fail", "replace", "append"],
        default="replace",
        help="Behavior when the table already exists.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    csv_path: Path = args.csv_path
    sqlite_path = args.output or csv_path.with_suffix(".db")
    table_name = args.table or normalize_table_name(csv_path.name)

    write_sqlite_table(
        csv_path=csv_path,
        sqlite_path=sqlite_path,
        table_name=table_name,
        date_columns=args.date_column,
        if_exists=args.if_exists,
    )

    print(f"wrote {sqlite_path} with table {table_name}")


if __name__ == "__main__":
    main()
