class MetaConst(type):
    def __setattr__(cls, name, value):
        if name in cls.__dict__:
            raise TypeError(f"Cannot rebind constant {name}")
        super().__setattr__(name, value)


class Constant(metaclass=MetaConst):
    LOGICAL_DELETE_FIELD = "is_deleted"