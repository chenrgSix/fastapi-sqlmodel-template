from entity.db_models import User
from service.base_service import BaseService


# 5. 具体服务类
class UserService(BaseService[User]):
    model = User  # 指定模型
