from entity.user import User
from service.base_service import BaseService


# 5. 具体服务类
class UserService(BaseService):
    model = User  # 指定模型
