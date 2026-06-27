from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str = ""


class UserCreate(UserBase):
    password: str = Field(min_length=6)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None


class UserOut(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PasswordChange(BaseModel):
    old_password: str
    new_password: str = Field(min_length=6)


class SalesRecordBase(BaseModel):
    product_name: str
    category: str = "未分类"
    region: str = "全国"
    sale_date: datetime
    quantity: int = Field(ge=0)
    unit_price: float = Field(ge=0)
    remark: str = ""


class SalesRecordCreate(SalesRecordBase):
    pass


class SalesRecordUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    region: Optional[str] = None
    sale_date: Optional[datetime] = None
    quantity: Optional[int] = Field(default=None, ge=0)
    unit_price: Optional[float] = Field(default=None, ge=0)
    remark: Optional[str] = None


class SalesRecordOut(SalesRecordBase):
    id: int
    amount: float
    created_by: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True


class ForecastRequest(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    periods: int = Field(default=6, ge=1, le=24)
    model_type: str = "linear"


class ForecastPoint(BaseModel):
    forecast_date: datetime
    predicted_quantity: float
    predicted_amount: float


class ForecastResult(BaseModel):
    product_name: str
    model_type: str
    confidence: float
    history_points: int
    forecasts: List[ForecastPoint]


class AnalysisSummary(BaseModel):
    total_records: int
    total_quantity: int
    total_amount: float
    product_count: int
    category_stats: List[dict]
    monthly_trend: List[dict]
    top_products: List[dict]


class SystemLogOut(BaseModel):
    id: int
    user_id: Optional[int]
    action: str
    detail: str
    ip_address: str
    created_at: datetime

    class Config:
        from_attributes = True


class SystemStats(BaseModel):
    user_count: int
    sales_count: int
    forecast_count: int
    total_sales_amount: float
