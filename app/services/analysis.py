from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import SalesRecord
from app.schemas import AnalysisSummary, ForecastPoint, ForecastResult


def build_sales_dataframe(
    db: Session,
    product_name: Optional[str] = None,
    category: Optional[str] = None,
) -> pd.DataFrame:
    query = db.query(SalesRecord)
    if product_name:
        query = query.filter(SalesRecord.product_name == product_name)
    if category:
        query = query.filter(SalesRecord.category == category)

    records = query.order_by(SalesRecord.sale_date).all()
    if not records:
        return pd.DataFrame()

    data = [
        {
            "sale_date": r.sale_date,
            "product_name": r.product_name,
            "category": r.category,
            "quantity": r.quantity,
            "amount": r.amount,
            "unit_price": r.unit_price,
        }
        for r in records
    ]
    return pd.DataFrame(data)


def get_analysis_summary(db: Session) -> AnalysisSummary:
    total_records = db.query(func.count(SalesRecord.id)).scalar() or 0
    total_quantity = db.query(func.sum(SalesRecord.quantity)).scalar() or 0
    total_amount = db.query(func.sum(SalesRecord.amount)).scalar() or 0.0
    product_count = (
        db.query(func.count(func.distinct(SalesRecord.product_name))).scalar() or 0
    )

    category_rows = (
        db.query(
            SalesRecord.category,
            func.sum(SalesRecord.quantity).label("quantity"),
            func.sum(SalesRecord.amount).label("amount"),
        )
        .group_by(SalesRecord.category)
        .all()
    )
    category_stats = [
        {"category": r.category, "quantity": int(r.quantity or 0), "amount": float(r.amount or 0)}
        for r in category_rows
    ]

    monthly_rows = (
        db.query(
            func.strftime("%Y-%m", SalesRecord.sale_date).label("month"),
            func.sum(SalesRecord.quantity).label("quantity"),
            func.sum(SalesRecord.amount).label("amount"),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    monthly_trend = [
        {"month": r.month, "quantity": int(r.quantity or 0), "amount": float(r.amount or 0)}
        for r in monthly_rows
    ]

    top_rows = (
        db.query(
            SalesRecord.product_name,
            func.sum(SalesRecord.quantity).label("quantity"),
            func.sum(SalesRecord.amount).label("amount"),
        )
        .group_by(SalesRecord.product_name)
        .order_by(func.sum(SalesRecord.amount).desc())
        .limit(10)
        .all()
    )
    top_products = [
        {"product_name": r.product_name, "quantity": int(r.quantity or 0), "amount": float(r.amount or 0)}
        for r in top_rows
    ]

    return AnalysisSummary(
        total_records=total_records,
        total_quantity=int(total_quantity),
        total_amount=float(total_amount),
        product_count=product_count,
        category_stats=category_stats,
        monthly_trend=monthly_trend,
        top_products=top_products,
    )


def run_forecast(
    db: Session,
    product_name: Optional[str],
    category: Optional[str],
    periods: int,
    model_type: str,
) -> ForecastResult:
    df = build_sales_dataframe(db, product_name, category)
    if df.empty:
        raise ValueError("没有可用的销售数据")

    if not product_name:
        product_name = df["product_name"].mode().iloc[0]

    df = df[df["product_name"] == product_name].copy()
    if df.empty:
        raise ValueError(f"产品 {product_name} 无销售记录")

    df["month"] = pd.to_datetime(df["sale_date"]).dt.to_period("M")
    monthly = (
        df.groupby("month")
        .agg(quantity=("quantity", "sum"), amount=("amount", "sum"), unit_price=("unit_price", "mean"))
        .reset_index()
    )
    monthly["month_dt"] = monthly["month"].dt.to_timestamp()

    if len(monthly) < 2:
        raise ValueError("至少需要2个月的历史数据才能预测")

    X = np.arange(len(monthly)).reshape(-1, 1)
    y_qty = monthly["quantity"].values
    y_amt = monthly["amount"].values
    avg_price = monthly["unit_price"].mean()

    if model_type == "moving_avg":
        window = min(3, len(monthly))
        base_qty = monthly["quantity"].tail(window).mean()
        base_amt = monthly["amount"].tail(window).mean()
        confidence = 0.6
        forecasts = []
        last_month = monthly["month_dt"].iloc[-1]
        for i in range(1, periods + 1):
            next_date = last_month + pd.DateOffset(months=i)
            forecasts.append(
                ForecastPoint(
                    forecast_date=next_date.to_pydatetime(),
                    predicted_quantity=round(float(base_qty), 2),
                    predicted_amount=round(float(base_amt), 2),
                )
            )
    else:
        model_qty = LinearRegression()
        model_amt = LinearRegression()
        model_qty.fit(X, y_qty)
        model_amt.fit(X, y_amt)
        confidence = float(max(0, min(r2_score(y_qty, model_qty.predict(X)), 1)))

        forecasts = []
        last_month = monthly["month_dt"].iloc[-1]
        for i in range(1, periods + 1):
            next_x = np.array([[len(monthly) - 1 + i]])
            pred_qty = max(0, float(model_qty.predict(next_x)[0]))
            pred_amt = max(0, float(model_amt.predict(next_x)[0]))
            next_date = last_month + pd.DateOffset(months=i)
            forecasts.append(
                ForecastPoint(
                    forecast_date=next_date.to_pydatetime(),
                    predicted_quantity=round(pred_qty, 2),
                    predicted_amount=round(pred_amt, 2),
                )
            )

    return ForecastResult(
        product_name=product_name,
        model_type=model_type,
        confidence=round(confidence, 4),
        history_points=len(monthly),
        forecasts=forecasts,
    )
