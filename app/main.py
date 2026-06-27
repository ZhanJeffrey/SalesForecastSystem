import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.auth import hash_password
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import SalesRecord, User
from app.routers import auth, forecast, sales, system


def init_database():
    os.makedirs("data", exist_ok=True)
    os.makedirs(settings.upload_dir, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                email="admin@example.com",
                full_name="系统管理员",
                hashed_password=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)
            db.commit()

        if db.query(SalesRecord).count() == 0:
            sample_data = [
                ("智能手机A", "电子产品", "华东", 120, 3999),
                ("智能手机A", "电子产品", "华南", 95, 3999),
                ("笔记本电脑B", "电子产品", "华北", 45, 6999),
                ("无线耳机C", "配件", "华东", 280, 299),
                ("平板电脑D", "电子产品", "西南", 60, 3299),
                ("智能手表E", "配件", "华东", 150, 1299),
                ("智能手机A", "电子产品", "华北", 110, 3999),
                ("笔记本电脑B", "电子产品", "华南", 52, 6999),
                ("无线耳机C", "配件", "华北", 310, 299),
                ("平板电脑D", "电子产品", "华东", 75, 3299),
            ]
            base_date = datetime(2024, 1, 1)
            admin = db.query(User).filter(User.username == "admin").first()
            for i, (name, cat, region, qty, price) in enumerate(sample_data):
                month_offset = i % 12
                sale_date = base_date + timedelta(days=30 * month_offset + i * 2)
                record = SalesRecord(
                    product_name=name,
                    category=cat,
                    region=region,
                    sale_date=sale_date,
                    quantity=qty + (i * 3),
                    unit_price=price,
                    amount=round((qty + i * 3) * price, 2),
                    created_by=admin.id if admin else None,
                )
                db.add(record)
            db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.include_router(auth.router)
app.include_router(sales.router)
app.include_router(forecast.router)
app.include_router(system.router)

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {"message": settings.app_name, "docs": "/docs"}
