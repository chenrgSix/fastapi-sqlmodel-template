from typing import List

from pydantic import BaseModel


class CpuInfo(BaseModel):
    cpu_num: int
    total: float
    sys: float
    used: float
    wait: float
    free: float


class SystemInfo(BaseModel):
    computerName: str
    computerIp: str
    userDir: str
    osName: str
    osArch: str


class DiskInfo(BaseModel):
    dirName: str
    sysTypeName: str
    typeName: str
    total: str  # 格式化大小，如 "1.20GB"
    free: str  # 格式化大小
    used: str  # 格式化大小
    usage: float  # 百分比


class MemoryInfo(BaseModel):
    total: float  # GB
    used: float  # GB
    free: float  # GB
    usage: float  # 百分比


class PythonEnvInfo(BaseModel):
    name: str
    version: str
    home: str
    inputArgs: str
    total: float  # MB
    max: float  # MB
    free: float  # MB
    usage: float  # MB
    runTime: str  # 格式化时间，如 "1天2小时30分钟"
    startTime: str  # 格式化时间


class ServerInfo(BaseModel):
    cpu: CpuInfo
    memory: MemoryInfo
    system: SystemInfo
    disks: List[DiskInfo]
    python: PythonEnvInfo
