import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from utils.api_utils import server_error_response
from .base import AppException

logger = logging.getLogger(__name__)


def configure_exception(app: FastAPI):
    """配置全局异常处理
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """处理自定义异常
            code: .
        """
        if exc.echo_exc:
            logging.error('app_exception_handler: url=[%s]', request.url.path)
            logging.error(exc, exc_info=True)
        return JSONResponse(
            status_code=200,
            content={'code': exc.code, 'message': exc.msg, 'data': False})

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors(), "body": exc.body}
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        return server_error_response(exc)
