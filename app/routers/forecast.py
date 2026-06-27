from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import ForecastRecord, User
from app.schemas import AnalysisSummary, ForecastRequest, ForecastResult
from app.services.analysis import get_analysis_summary, run_forecast
from app.services.data_import import log_action

router = APIRouter(prefix="/api/forecast", tags=["数据预测"])


@router.get("/analysis", response_model=AnalysisSummary)
def get_analysis(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return get_analysis_summary(db)


@router.post("/predict", response_model=ForecastResult)
def predict(
    req: ForecastRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        result = run_forecast(
            db,
            product_name=req.product_name,
            category=req.category,
            periods=req.periods,
            model_type=req.model_type,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    for point in result.forecasts:
        record = ForecastRecord(
            product_name=result.product_name,
            forecast_date=point.forecast_date,
            predicted_quantity=point.predicted_quantity,
            predicted_amount=point.predicted_amount,
            model_type=result.model_type,
            confidence=result.confidence,
            created_by=current_user.id,
        )
        db.add(record)
    db.commit()

    log_action(
        db,
        current_user.id,
        "销量预测",
        f"产品: {result.product_name}, 模型: {result.model_type}, 周期: {req.periods}",
    )
    return result


@router.get("/history")
def forecast_history(
    limit: int = 20,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    records = (
        db.query(ForecastRecord)
        .order_by(ForecastRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": r.id,
            "product_name": r.product_name,
            "forecast_date": r.forecast_date,
            "predicted_quantity": r.predicted_quantity,
            "predicted_amount": r.predicted_amount,
            "model_type": r.model_type,
            "confidence": r.confidence,
            "created_at": r.created_at,
        }
        for r in records
    ]
