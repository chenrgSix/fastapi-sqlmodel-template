from fastapi import APIRouter, Query

from entity.dto.UserDto import UserQueryPageReq
from service.user_service import UserService

router = APIRouter(prefix="/user", tags=["用户"])
base_service = UserService
@router.get("/page")
async def page(req:UserQueryPageReq=Query(...)):
    return await base_service.get_by_page(req)