from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import SalesRecord, User
from app.schemas import SalesRecordCreate, SalesRecordOut, SalesRecordUpdate
from app.services.data_import import import_sales_records, log_action, parse_sales_file

router = APIRouter(prefix="/api/sales", tags=["数据管理"])


@router.get("", response_model=List[SalesRecordOut])
def list_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    product_name: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(SalesRecord)
    if product_name:
        query = query.filter(SalesRecord.product_name.contains(product_name))
    if category:
        query = query.filter(SalesRecord.category == category)
    return query.order_by(SalesRecord.sale_date.desc()).offset(skip).limit(limit).all()


@router.get("/products")
def list_products(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(SalesRecord.product_name).distinct().all()
    return [r[0] for r in rows]


@router.get("/categories")
def list_categories(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rows = db.query(SalesRecord.category).distinct().all()
    return [r[0] for r in rows]


@router.post("", response_model=SalesRecordOut)
def create_sales(
    data: SalesRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = SalesRecord(
        **data.model_dump(),
        amount=round(data.quantity * data.unit_price, 2),
        created_by=current_user.id,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    log_action(db, current_user.id, "新增销售记录", f"产品: {data.product_name}")
    return record


@router.put("/{record_id}", response_model=SalesRecordOut)
def update_sales(
    record_id: int,
    data: SalesRecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(SalesRecord).filter(SalesRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(record, key, value)
    record.amount = round(record.quantity * record.unit_price, 2)
    db.commit()
    db.refresh(record)
    log_action(db, current_user.id, "更新销售记录", f"ID: {record_id}")
    return record


@router.delete("/{record_id}")
def delete_sales(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(SalesRecord).filter(SalesRecord.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(record)
    db.commit()
    log_action(db, current_user.id, "删除销售记录", f"ID: {record_id}")
    return {"message": "删除成功"}


@router.post("/import")
async def import_sales(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="未选择文件")
    content = await file.read()
    try:
        records = parse_sales_file(content, file.filename)
        count = import_sales_records(db, records, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    log_action(db, current_user.id, "批量导入", f"导入 {count} 条记录，文件: {file.filename}")
    return {"message": f"成功导入 {count} 条记录", "count": count}
