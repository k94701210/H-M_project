import os
import pandas as pd
import pyodbc
from datetime import datetime

# =========================
# 路徑設定
# =========================
BASE_DIR = r"C:\Projects\H-M_project"
DATA_DIR = os.path.join(BASE_DIR, "dataset")
LOG_DIR = os.path.join(BASE_DIR, "GPT_logs")

ARTICLES_FILE = os.path.join(DATA_DIR, "articles.csv")
CUSTOMERS_FILE = os.path.join(DATA_DIR, "customers.csv")
TRANSACTIONS_FILE = os.path.join(DATA_DIR, "transactions_train.csv")

os.makedirs(LOG_DIR, exist_ok=True)

# =========================
# DB 連線設定
# =========================
CONN_STR = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=HM_Analytics;"
    "Trusted_Connection=yes;"
)

CHUNK_SIZE = 200000 


# =========================
# 工具函式
# =========================
def get_connection():
    conn = pyodbc.connect(CONN_STR)
    conn.autocommit = False
    return conn


def log_message(msg: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{now}] {msg}")
    with open(os.path.join(LOG_DIR, "etl_log.txt"), "a", encoding="utf-8") as f:
        f.write(f"[{now}] {msg}\n")


def truncate_table(table_name: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"TRUNCATE TABLE {table_name}")
    conn.commit()
    cur.close()
    conn.close()
    log_message(f"已清空 {table_name}")


def calculate_null_ratio(df: pd.DataFrame) -> dict:
    total_rows = len(df)
    result = {}
    for col in df.columns:
        if total_rows == 0:
            result[col] = {"null_count": 0, "null_ratio": 0.0}
        else:
            null_count = int(df[col].isna().sum())
            null_ratio = null_count / total_rows
            result[col] = {"null_count": null_count, "null_ratio": null_ratio}
    return result


def write_summary_txt(report_name: str, raw_count: int, clean_count: int, null_ratio_dict: dict):
    file_path = os.path.join(LOG_DIR, report_name)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write("QA 報告\n")
        f.write("=" * 50 + "\n")
        f.write(f"原始總筆數: {raw_count:,}\n")
        f.write(f"清洗後剩餘筆數: {clean_count:,}\n")
        f.write(f"移除筆數: {raw_count - clean_count:,}\n")
        f.write("\n各欄位 Null 值比例:\n")
        f.write("-" * 50 + "\n")
        for col, stat in null_ratio_dict.items():
            f.write(
                f"{col}: Null={stat['null_count']:,}, "
                f"Ratio={stat['null_ratio']:.4%}\n"
            )


def append_batch_summary(summary_file: str, row: dict):
    df = pd.DataFrame([row])
    if not os.path.exists(summary_file):
        df.to_csv(summary_file, index=False, encoding="utf-8-sig")
    else:
        df.to_csv(summary_file, mode="a", header=False, index=False, encoding="utf-8-sig")


def to_python_records(df: pd.DataFrame, cols: list[str]) -> list[tuple]:
    """
    轉成 pyodbc 穩定可用的 Python 原生型別：
    - NaN / <NA> -> None
    - numpy scalar -> Python scalar
    """
    rows = []
    for row in df[cols].itertuples(index=False, name=None):
        clean_row = []
        for val in row:
            if pd.isna(val):
                clean_row.append(None)
            elif hasattr(val, "item"):  # numpy scalar
                clean_row.append(val.item())
            else:
                clean_row.append(val)
        rows.append(tuple(clean_row))
    return rows


# =========================
# 匯入 articles
# =========================
def load_articles_to_staging():
    log_message("開始匯入 stg_articles")

    df = pd.read_csv(ARTICLES_FILE, dtype=str)
    raw_count = len(df)

    # 你已經把 staging 代碼欄位改成 VARCHAR 後，
    # 這裡直接保留字串最穩定
    code_cols = [
        "product_type_no", "graphical_appearance_no", "colour_group_code",
        "perceived_colour_value_id", "perceived_colour_master_id",
        "department_no", "index_group_no", "section_no", "garment_group_no"
    ]

    for col in code_cols:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "nan", "None", "<NA>"]), col] = None

    # 其他欄位也統一去前後空白
    str_cols = [c for c in df.columns if c not in code_cols]
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "nan", "None", "<NA>"]), col] = None

    null_ratio_dict = calculate_null_ratio(df)
    write_summary_txt("articles_summary.txt", raw_count, len(df), null_ratio_dict)

    cols = [
        "article_id", "product_code", "prod_name", "product_type_no", "product_type_name",
        "product_group_name", "graphical_appearance_no", "graphical_appearance_name",
        "colour_group_code", "colour_group_name", "perceived_colour_value_id",
        "perceived_colour_value_name", "perceived_colour_master_id", "perceived_colour_master_name",
        "department_no", "department_name", "index_code", "index_name", "index_group_no",
        "index_group_name", "section_no", "section_name", "garment_group_no",
        "garment_group_name", "detail_desc"
    ]

    sql = f"""
    INSERT INTO dbo.stg_articles (
        {",".join(cols)}
    ) VALUES (
        {",".join(["?"] * len(cols))}
    )
    """

    records = to_python_records(df, cols)

    conn = get_connection()
    cur = conn.cursor()
    cur.fast_executemany = True
    cur.executemany(sql, records)
    conn.commit()
    cur.close()
    conn.close()

    log_message(f"stg_articles 匯入完成，筆數={len(df)}")


# =========================
# 匯入 customers
# =========================
def load_customers_to_staging():
    log_message("開始匯入 stg_customers")

    df = pd.read_csv(CUSTOMERS_FILE, dtype=str)
    raw_count = len(df)

    # 字串欄位清理
    str_cols = ["customer_id", "FN", "Active", "club_member_status", "fashion_news_frequency", "postal_code"]
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
        df.loc[df[col].isin(["", "nan", "None", "<NA>"]), col] = None

    # 年齡轉數值
    df["age"] = pd.to_numeric(df["age"], errors="coerce")

    null_ratio_dict = calculate_null_ratio(df)
    write_summary_txt("customers_summary.txt", raw_count, len(df), null_ratio_dict)

    cols = [
        "customer_id", "FN", "Active", "club_member_status",
        "fashion_news_frequency", "age", "postal_code"
    ]

    sql = f"""
    INSERT INTO dbo.stg_customers (
        {",".join(cols)}
    ) VALUES (
        {",".join(["?"] * len(cols))}
    )
    """

    records = to_python_records(df, cols)

    conn = get_connection()
    cur = conn.cursor()
    cur.fast_executemany = True
    cur.executemany(sql, records)
    conn.commit()
    cur.close()
    conn.close()

    log_message(f"stg_customers 匯入完成，筆數={len(df)}")


# =========================
# 清洗 transactions chunk
# =========================
def clean_transactions_chunk(df: pd.DataFrame, batch_id: int):
    raw_count = len(df)

    # 先算原始欄位 Null 比例（可選）
    raw_null_ratio_dict = calculate_null_ratio(df)

    # 清洗
    df["t_dat"] = pd.to_datetime(df["t_dat"], errors="coerce").dt.date
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["sales_channel_id"] = pd.to_numeric(df["sales_channel_id"], errors="coerce")

    # 文字欄位清理
    df["customer_id"] = df["customer_id"].astype(str).str.strip()
    df["article_id"] = df["article_id"].astype(str).str.strip()

    df.loc[df["customer_id"].isin(["", "nan", "None", "<NA>"]), "customer_id"] = None
    df.loc[df["article_id"].isin(["", "nan", "None", "<NA>"]), "article_id"] = None

    # 去除關鍵欄位空值
    df = df[
        df["t_dat"].notna() &
        df["customer_id"].notna() &
        df["article_id"].notna() &
        df["price"].notna()
    ].copy()

    # 補 ETL 欄位
    df["batch_id"] = int(batch_id)
    df["row_num_in_batch"] = range(1, len(df) + 1)

    # article_id 補零成 10 碼
    df["article_id"] = df["article_id"].astype(str).str.zfill(10)

    clean_count = len(df)
    removed_count = raw_count - clean_count
    clean_null_ratio_dict = calculate_null_ratio(df)

    log_message(f"batch {batch_id}: 原始={raw_count}, 清洗後={clean_count}, 移除={removed_count}")

    # 每批 QA 報告
    write_summary_txt(
        f"transactions_batch_{batch_id}_summary.txt",
        raw_count,
        clean_count,
        clean_null_ratio_dict
    )

    # 批次摘要 CSV
    summary_file = os.path.join(LOG_DIR, "transactions_cleaning_summary.csv")
    append_batch_summary(summary_file, {
        "batch_id": batch_id,
        "raw_count": raw_count,
        "clean_count": clean_count,
        "removed_count": removed_count
    })

    return df, {
        "batch_id": batch_id,
        "raw_count": raw_count,
        "clean_count": clean_count,
        "removed_count": removed_count,
        "raw_null_ratio_dict": raw_null_ratio_dict,
        "clean_null_ratio_dict": clean_null_ratio_dict
    }


# =========================
# 分批匯入 transactions
# =========================
def load_transactions_to_staging():
    log_message("開始分批匯入 stg_transactions")

    insert_cols = [
        "t_dat", "customer_id", "article_id", "price",
        "sales_channel_id", "batch_id", "row_num_in_batch"
    ]

    sql = f"""
    INSERT INTO dbo.stg_transactions (
        {",".join(insert_cols)}
    ) VALUES (
        {",".join(["?"] * len(insert_cols))}
    )
    """

    batch_id = 0
    total_raw_count = 0
    total_clean_count = 0
    aggregated_null_counts = {}

    for chunk in pd.read_csv(
        TRANSACTIONS_FILE,
        dtype={"customer_id": str, "article_id": str},
        chunksize=CHUNK_SIZE
    ):
        batch_id += 1
        log_message(f"讀取 batch {batch_id}，筆數={len(chunk)}")

        chunk, batch_stats = clean_transactions_chunk(chunk, batch_id)

        total_raw_count += batch_stats["raw_count"]
        total_clean_count += batch_stats["clean_count"]

        for col, stat in batch_stats["clean_null_ratio_dict"].items():
            aggregated_null_counts[col] = aggregated_null_counts.get(col, 0) + stat["null_count"]

        records = to_python_records(chunk, insert_cols)

        conn = get_connection()
        cur = conn.cursor()
        cur.fast_executemany = True
        cur.executemany(sql, records)
        conn.commit()
        cur.close()
        conn.close()

        log_message(f"batch {batch_id} 已寫入 stg_transactions，筆數={len(chunk)}")

    # 全部批次彙總 QA
    final_null_ratio_dict = {}
    for col, null_count in aggregated_null_counts.items():
        ratio = 0.0 if total_clean_count == 0 else null_count / total_clean_count
        final_null_ratio_dict[col] = {
            "null_count": int(null_count),
            "null_ratio": ratio
        }

    write_summary_txt("summary.txt", total_raw_count, total_clean_count, final_null_ratio_dict)

    log_message("stg_transactions 全部匯入完成")
    log_message("已產出 summary.txt")


# =========================
# 主流程
# =========================
def run_etl():
    truncate_table("dbo.stg_articles")
    truncate_table("dbo.stg_customers")
    truncate_table("dbo.stg_transactions")

    load_articles_to_staging()
    load_customers_to_staging()
    load_transactions_to_staging()

    log_message("ETL staging 完成")


if __name__ == "__main__":
    run_etl()
