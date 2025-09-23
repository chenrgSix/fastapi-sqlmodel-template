# RG-FastAPI-SQLModel 模板项目

一个基于FastAPI和SQLModel的现代化Python Web应用模板，提供了快速开发RESTful API的基础架构。

## 项目特点

- 基于FastAPI构建的高性能异步Web框架
- 使用SQLModel进行数据库ORM操作，结合了SQLAlchemy和Pydantic的优点
- 完整的项目结构，包括路由、服务层、实体模型和DTO
- 内置异常处理机制
- 中间件支持，包括数据库会话管理
- 实用工具集合，包括日志、文件操作、IP工具等

## 项目结构

```
├── common/               # 通用模块，包含常量和枚举
├── config/               # 配置模块
├── core/                 # 核心功能模块
├── entity/               # 实体模型定义
│   └── dto/              # 数据传输对象
├── exceptions/           # 异常处理模块
├── middleware/           # 中间件模块
├── router/               # API路由模块
├── service/              # 业务服务层
├── utils/                # 工具函数模块
├── main.py               # 应用入口
├── pyproject.toml        # 项目依赖配置
└── .env.template         # 环境变量模板
```

## 技术栈

- Python 3.12+
- FastAPI 0.116.1+
- SQLModel 0.0.25+
- SQLAlchemy 2.0.43+ (异步支持)
- 其他依赖详见pyproject.toml

## 快速开始

### 环境准备

1. 确保已安装Python 3.12或更高版本
2. 安装依赖管理工具uv (推荐)

### 安装依赖

```bash
# 初始化环境 如果没有 uv需自行安装 pip install uv
uv sync
# 如需使用uv安装依赖
uv add xxx
```

### 配置环境变量

```bash
# 复制环境变量模板并修改
cp .env.template .env
# 如需启用YAML 配置文件支持，需要将.env中 的LOAD_YAML设置为 true，并执行以下操作
cp application-template.yaml application.yaml
# 根据需要编辑.env和application.yaml文件
```

### 启动服务

```bash
# 开发环境启动
python main.py
```

## API路由

- `/monitor` - 系统监控相关API
- `/user` - 用户相关API

## 开发指南

### 添加新实体

1. 在`entity`目录下创建新的实体模型
2. 在`entity/dto`目录下创建对应的DTO
3. 在`service`目录下创建对应的服务层
4. 在`router`目录下创建对应的API路由

### 异常处理

项目提供了统一的异常处理机制，可在`exceptions`目录下扩展自定义异常。

