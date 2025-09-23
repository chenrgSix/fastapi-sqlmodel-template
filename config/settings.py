from functools import lru_cache

from dotenv import load_dotenv
from pydantic.v1 import BaseSettings as Base

from utils import file_utils


class BaseSettings(Base):
    """配置基类"""

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'allow'


class Settings(BaseSettings):
    """应用配置
        server目录为后端项目根目录, 在该目录下创建 "config.env" 文件, 写入环境变量(默认大写)会自动加载, 并覆盖同名配置(小写)
            eg.
            config.env 文件内写入
                REDIS_URL='redis://localhost:6379'
                上述环境变量会覆盖 redis_url
    """
    # 模式
    mode: str = 'dev'  # dev, prod
    debug: bool = False  # dev, prod
    load_yaml: bool = True # 是否开启加载 yaml 配置文件
    conf_yaml_name: str = 'application.yaml'  # dev, prod
    # 版本
    api_version: str = '/v1'
    # 时区
    timezone: str = 'Asia/Shanghai'
    # 日期时间格式
    datetime_fmt: str = '%Y-%m-%d %H:%M:%S'
    # Redis键前缀
    redis_prefix: str = 'agent:'
    # 当前域名
    host_ip: str = '0.0.0.0'
    host_port: int = 8080
    # sql驱动连接
    database_url: str = ''

    # yaml配置
    yaml_config: dict = {}


@lru_cache()
def get_settings() -> Settings:
    """获取并缓存应用配置"""
    # 读取server目录下的配置
    load_dotenv()
    settings = Settings()
    if settings.load_yaml:
        yaml_config = file_utils.load_yaml_conf(settings.conf_yaml_name)
        # 将YAML配置存储到Settings实例中
        settings.yaml_config = yaml_config
        for k, v in settings.yaml_config.items():
            if not hasattr(settings, k) or getattr(settings, k) == settings.__fields__[k].default:
                setattr(settings, k, v)
    return settings
