import logging

from fastapi import APIRouter, Depends

from server_info import ServerInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix='/monitor', tags=["缓存监控服务"])


@router.get('/server',summary='服务监控')
def monitor_server():
    """服务器信息监控"""
    return {
        'cpu': ServerInfo.get_cpu_info(),
        'mem': ServerInfo.get_mem_info(),
        'sys': ServerInfo.get_sys_info(),
        'disk': ServerInfo.get_disk_info(),
        'py': ServerInfo.get_py_info(),
    }
