import logging

from fastapi import APIRouter

from entity.dto.monitor_dto import ServerInfo
from router import unified_resp
from utils.server_info_utils import ServerInfoUtils

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/monitor', tags=["缓存监控服务"])


@router.get('/server', summary='服务监控')
@unified_resp
def monitor_server() -> ServerInfo:
    """服务器信息监控"""
    return ServerInfo(
        cpu=ServerInfoUtils.get_cpu_info(),
        memory=ServerInfoUtils.get_mem_info(),
        system=ServerInfoUtils.get_sys_info(),
        disks=ServerInfoUtils.get_disk_info(),
        python=ServerInfoUtils.get_py_info()
    )
