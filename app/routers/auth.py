from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import PasswordChange, Token, UserCreate, UserOut, UserUpdate
from app.services.data_import import log_action

router = APIRouter(prefix="/api/auth", tags=["用户中心"])


@router.post("/register", response_model=UserOut)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册")

    user = User(
        username=user_in.username,
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=hash_password(user_in.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="账户已被禁用")

    token = create_access_token(data={"sub": user.username})
    log_action(db, user.id, "用户登录", f"用户 {user.username} 登录系统")
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
def update_me(
    update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if update.email:
        existing = db.query(User).filter(User.email == update.email, User.id != current_user.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        current_user.email = update.email
    if update.full_name is not None:
        current_user.full_name = update.full_name
    if update.password:
        current_user.hashed_password = hash_password(update.password)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    log_action(db, current_user.id, "更新个人信息", "用户更新了个人资料")
    return current_user


@router.post("/change-password")
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="原密码不正确")
    current_user.hashed_password = hash_password(data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()
    log_action(db, current_user.id, "修改密码", "用户修改了密码")
    return {"message": "密码修改成功"}
