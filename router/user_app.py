from fastapi import APIRouter, Query

from entity.dto.UserDto import UserQueryPageReq, UserQueryReq
from router import BaseController
from service.user_service import UserService

router = APIRouter(prefix="/user", tags=["用户"])
base_service = UserService
base_app = BaseController(base_service)

@router.get("/page")
async def get_page(req:UserQueryPageReq=Query(...)):
    return await base_service.get_by_page(req)

@router.get("/list")
async def get_list(req:UserQueryReq=Query(...)):
    return await base_service.get_list(req)
