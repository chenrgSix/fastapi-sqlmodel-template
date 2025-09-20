from fastapi import APIRouter

from config import settings
from utils.file_utils import get_project_base_directory

router = APIRouter()

@router.get("/test")
async def test():
    return {
        "settings":settings,
        "base_path": get_project_base_directory(),
    }