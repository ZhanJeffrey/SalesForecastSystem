from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), default="")
    role = Column(String(20), default="user")  # admin, user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    sales_records = relationship("SalesRecord", back_populates="creator")


class SalesRecord(Base):
    __tablename__ = "sales_records"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), default="未分类")
    region = Column(String(50), default="全国")
    sale_date = Column(DateTime, nullable=False, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    unit_price = Column(Float, nullable=False, default=0.0)
    amount = Column(Float, nullable=False, default=0.0)
    remark = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="sales_records")


class ForecastRecord(Base):
    __tablename__ = "forecast_records"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String(100), nullable=False)
    category = Column(String(50), default="")
    forecast_date = Column(DateTime, nullable=False)
    predicted_quantity = Column(Float, nullable=False)
    predicted_amount = Column(Float, nullable=False)
    model_type = Column(String(50), default="linear")
    confidence = Column(Float, default=0.0)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(100), nullable=False)
    detail = Column(Text, default="")
    ip_address = Column(String(50), default="")
    created_at = Column(DateTime, default=datetime.utcnow)
