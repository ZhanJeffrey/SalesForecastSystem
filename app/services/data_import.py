from datetime import datetime
from io import BytesIO
from typing import List, Optional

import pandas as pd
from sqlalchemy.orm import Session

from app.models import SalesRecord, SystemLog


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    detail: str = "",
    ip_address: str = "",
):
    log = SystemLog(
        user_id=user_id,
        action=action,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()


def parse_sales_file(content: bytes, filename: str) -> List[dict]:
    if filename.endswith((".xlsx", ".xls")):
        df = pd.read_excel(BytesIO(content))
    elif filename.endswith(".csv"):
        df = pd.read_csv(BytesIO(content))
    else:
        raise ValueError("仅支持 CSV 或 Excel 文件")

    column_map = {
        "产品名称": "product_name",
        "产品": "product_name",
        "product_name": "product_name",
        "分类": "category",
        "category": "category",
        "区域": "region",
        "region": "region",
        "销售日期": "sale_date",
        "日期": "sale_date",
        "sale_date": "sale_date",
        "数量": "quantity",
        "quantity": "quantity",
        "单价": "unit_price",
        "unit_price": "unit_price",
        "备注": "remark",
        "remark": "remark",
    }

    df = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})

    required = {"product_name", "sale_date", "quantity", "unit_price"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"缺少必要列: {', '.join(missing)}")

    records = []
    for _, row in df.iterrows():
        sale_date = pd.to_datetime(row["sale_date"])
        quantity = int(row["quantity"])
        unit_price = float(row["unit_price"])
        records.append(
            {
                "product_name": str(row["product_name"]),
                "category": str(row.get("category", "未分类")),
                "region": str(row.get("region", "全国")),
                "sale_date": sale_date.to_pydatetime(),
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": round(quantity * unit_price, 2),
                "remark": str(row.get("remark", "")),
            }
        )
    return records


def import_sales_records(db: Session, records: List[dict], user_id: int) -> int:
    count = 0
    for item in records:
        record = SalesRecord(**item, created_by=user_id)
        db.add(record)
        count += 1
    db.commit()
    return count
