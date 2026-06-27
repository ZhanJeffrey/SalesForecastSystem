from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth import get_admin_user, get_current_user, hash_password
from app.database import get_db
from app.models import ForecastRecord, SalesRecord, SystemLog, User
from app.schemas import SystemLogOut, SystemStats, UserOut
from app.services.data_import import log_action

router = APIRouter(prefix="/api/system", tags=["系统管理"])


@router.get("/stats", response_model=SystemStats)
def system_stats(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return SystemStats(
        user_count=db.query(func.count(User.id)).scalar() or 0,
        sales_count=db.query(func.count(SalesRecord.id)).scalar() or 0,
        forecast_count=db.query(func.count(ForecastRecord.id)).scalar() or 0,
        total_sales_amount=float(db.query(func.sum(SalesRecord.amount)).scalar() or 0),
    )


@router.get("/logs", response_model=List[SystemLogOut])
def system_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    return (
        db.query(SystemLog)
        .order_by(SystemLog.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/users", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.put("/users/{user_id}/toggle")
def toggle_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能禁用当前账户")

    user.is_active = not user.is_active
    db.commit()
    status_text = "启用" if user.is_active else "禁用"
    log_action(db, admin.id, "用户管理", f"{status_text}用户: {user.username}")
    return {"message": f"已{status_text}用户 {user.username}"}


@router.put("/users/{user_id}/reset-password")
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    user.hashed_password = hash_password("123456")
    db.commit()
    log_action(db, admin.id, "重置密码", f"重置用户 {user.username} 的密码")
    return {"message": f"已将 {user.username} 的密码重置为 123456"}


@router.delete("/logs")
def clear_logs(db: Session = Depends(get_db), admin: User = Depends(get_admin_user)):
    count = db.query(SystemLog).delete()
    db.commit()
    log_action(db, admin.id, "清空日志", f"清空了 {count} 条系统日志")
    return {"message": f"已清空 {count} 条日志"}
