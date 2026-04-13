import os
import math
import pandas as pd
import pyodbc
import pyarrow as pa
import pyarrow.parquet as pq
from datetime import datetime


# =========================================================
# 1. 基本設定
# =========================================================
BASE_DIR = r"C:\Projects\H-M_project"
EXPORT_DIR = os.path.join(BASE_DIR, "parquet_exports")

os.makedirs(EXPORT_DIR, exist_ok=True)

CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=HM_Analytics;"
    "Trusted_Connection=yes;"
)

# 大表建議分批讀
CHUNK_SIZE = 200000


# =========================================================
# 2. 工具函式
# =========================================================
def log(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")


def get_connection():
    return pyodbc.connect(CONN_STR)


def get_table_row_count(table_name: str) -> int:
    sql = f"SELECT COUNT(*) AS cnt FROM {table_name}"
    with get_connection() as conn:
        row = pd.read_sql(sql, conn).iloc[0]
        return int(row["cnt"])


def export_small_table_to_parquet(table_name: str, output_file: str):
    """
    小表：一次讀完直接輸出
    適合 dim / agg
    """
    log(f"開始匯出小表：{table_name}")

    sql = f"SELECT * FROM {table_name}"

    with get_connection() as conn:
        df = pd.read_sql(sql, conn)

    df.to_parquet(output_file, engine="pyarrow", index=False)

    log(f"完成：{table_name} -> {output_file}，筆數={len(df):,}")


def export_large_table_to_parquet(table_name: str, output_file: str, chunk_size: int = 200000):
    """
    大表：分批讀取，逐批寫入同一個 parquet
    適合 fact table
    """
    log(f"開始匯出大表：{table_name}")

    total_rows = get_table_row_count(table_name)
    log(f"{table_name} 總筆數：{total_rows:,}")

    writer = None
    offset = 0
    batch_no = 0
    total_exported = 0

    try:
        while offset < total_rows:
            batch_no += 1

            sql = f"""
            SELECT *
            FROM {table_name}
            ORDER BY (SELECT NULL)
            OFFSET {offset} ROWS
            FETCH NEXT {chunk_size} ROWS ONLY
            """

            with get_connection() as conn:
                df_chunk = pd.read_sql(sql, conn)

            if df_chunk.empty:
                break

            table = pa.Table.from_pandas(df_chunk, preserve_index=False)

            if writer is None:
                writer = pq.ParquetWriter(output_file, table.schema)

            writer.write_table(table)

            total_exported += len(df_chunk)
            log(
                f"{table_name} 第 {batch_no} 批完成，"
                f"本批={len(df_chunk):,}，累計={total_exported:,}"
            )

            offset += chunk_size

    finally:
        if writer is not None:
            writer.close()

    log(f"完成：{table_name} -> {output_file}，總筆數={total_exported:,}")


def export_table(table_name: str, is_large: bool = False, chunk_size: int = 200000):
    """
    自動依表大小選擇匯出方式
    """
    safe_name = table_name.replace("dbo.", "")
    output_file = os.path.join(EXPORT_DIR, f"{safe_name}.parquet")

    if is_large:
        export_large_table_to_parquet(table_name, output_file, chunk_size=chunk_size)
    else:
        export_small_table_to_parquet(table_name, output_file)


# =========================================================
# 3. 主程式
# =========================================================
def run_export():
    log("=== 開始匯出 SQL Server 資料表到 Parquet ===")

    # 你的 HM 專題目前主要表
    tables_to_export = [
        {"table_name": "dbo.dim_articles",        "is_large": False},
        {"table_name": "dbo.dim_customers",       "is_large": False},
        {"table_name": "dbo.fact_transactions",   "is_large": True},
        {"table_name": "dbo.agg_sales_monthly",   "is_large": False},
        {"table_name": "dbo.agg_article_monthly", "is_large": False},
        {"table_name": "dbo.agg_customer_monthly","is_large": False},
    ]

    for item in tables_to_export:
        export_table(
            table_name=item["table_name"],
            is_large=item["is_large"],
            chunk_size=CHUNK_SIZE
        )

    log("=== 全部匯出完成 ===")
    log(f"輸出資料夾：{EXPORT_DIR}")


if __name__ == "__main__":
    run_export()