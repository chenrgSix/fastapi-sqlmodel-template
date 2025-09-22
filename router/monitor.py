import logging

from fastapi import APIRouter

from router import unified_resp
from utils.server_info_utils import ServerInfoUtils

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/monitor', tags=["缓存监控服务"])


@router.get('/server',summary='服务监控')
@unified_resp
def monitor_server():
    """服务器信息监控"""
    return {
        'cpu': ServerInfoUtils.get_cpu_info(),
        'mem': ServerInfoUtils.get_mem_info(),
        'sys': ServerInfoUtils.get_sys_info(),
        'disk': ServerInfoUtils.get_disk_info(),
        'py': ServerInfoUtils.get_py_info(),
    }
