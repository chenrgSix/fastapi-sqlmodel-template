import secrets
import sys
from contextlib import asynccontextmanager
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import List

import anyio.to_thread
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from config import settings

__all__ = ["app"]

from middleware import add_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    current_default_thread_limiter()：官方文档里的唯一合法入口
    total_tokens：不是线程数，而是并发通行证，令牌用光就排队
    官方建议：不要盲目拉满，CPU核心数*5是一个经验上限
    """
    # 1. 拿到当前全局限速器
    limiter = anyio.to_thread.current_default_thread_limiter()
    # 2. 把40个线程改成80
    limiter.total_tokens = 80
    yield


# FastAPI应用初始化
app = FastAPI(
    title="DataBuilder API",
    description="数据工厂 api",
    version="1.0.0",
    lifespan=lifespan
)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="数据工厂",
        version="1.0.0",
        description="数据工厂接口文档",
        routes=app.routes,
    )

    # # 添加全局安全方案
    # openapi_schema["components"]["securitySchemes"] = {
    #     "global_auth": {
    #         "type": "apiKey",
    #         "in": "header",
    #         "name": "Authorization"  # 这里可以改为任何需要的请求头名称
    #     }
    # }

    # 应用全局安全要求
    openapi_schema["security"] = [
        {"global_auth": []}
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi

# 全局异常处理
# configure_exception(app)
# 中间件
add_middleware(app=app)
white_list = ["/docs", "/openapi.json", "/redoc"]


# 动态路由注册
def search_pages_path(pages_dir: Path) -> List[Path]:
    return [path for path in pages_dir.glob("*.py") if not path.name.startswith(".") and not path.name.startswith("_")]


def register_controller(page_path: Path, prefix=settings.api_version):
    module_name = f"router.{page_path.stem}"
    spec = spec_from_file_location(module_name, page_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {page_path}")

    page = module_from_spec(spec)
    sys.modules[module_name] = page
    spec.loader.exec_module(page)

    # 注册路由
    if hasattr(page, "router"):
        app.include_router(page.router, prefix=prefix)
    return page.router if page.router else prefix


# 注册所有控制器
pages_dirs = [
    Path(__file__).parent.parent / "router",
]

client_urls_prefix = [
    register_controller(path)
    for pages_dir in pages_dirs
    for path in search_pages_path(pages_dir)
]
