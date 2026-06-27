# 销量分析与预测系统

基于 Python FastAPI 的轻量级销量分析与预测系统，前端采用原生 HTML/CSS/JS，界面简洁，部署方便。

## 功能模块

| 模块 | 功能 |
|------|------|
| **用户中心** | 登录/注册、个人信息管理、密码修改 |
| **数据管理** | 销售数据增删改查、CSV/Excel 批量导入 |
| **数据预测** | 数据概览分析、线性回归/移动平均销量预测 |
| **系统管理** | 用户管理、系统日志、统计数据（管理员） |

## 技术栈

- **后端**: FastAPI + SQLAlchemy + SQLite
- **预测**: pandas + scikit-learn
- **前端**: 原生 HTML/CSS/JS + Chart.js
- **认证**: JWT Token

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动服务

```bash
python run.py
```

### 3. 访问系统

浏览器打开 [http://localhost:8000](http://localhost:8000)

- 默认管理员账号: `admin` / `admin123`
- API 文档: [http://localhost:8000/docs](http://localhost:8000/docs)

## 项目结构

```
SalesForecastSystem/
├── app/
│   ├── main.py          # 应用入口
│   ├── config.py        # 配置
│   ├── database.py      # 数据库连接
│   ├── models.py        # 数据模型
│   ├── schemas.py       # API 模式
│   ├── auth.py          # 认证工具
│   ├── routers/         # API 路由
│   └── services/        # 业务逻辑
├── static/              # 前端静态文件
├── data/                # SQLite 数据库（自动生成）
├── requirements.txt
└── run.py
```

## 数据导入格式

支持 CSV 或 Excel，需包含以下列：

| 列名 | 必填 | 说明 |
|------|------|------|
| 产品名称 | 是 | 产品名称 |
| 销售日期 | 是 | 日期格式 |
| 数量 | 是 | 销售数量 |
| 单价 | 是 | 单位价格 |
| 分类 | 否 | 产品分类 |
| 区域 | 否 | 销售区域 |
| 备注 | 否 | 备注信息 |

## 预测模型

- **线性回归**: 基于历史月度数据的趋势外推，提供 R² 置信度
- **移动平均**: 基于近 3 个月均值的平稳预测

## 配置

可通过 `.env` 文件覆盖默认配置：

```env
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///./data/sales.db
```
