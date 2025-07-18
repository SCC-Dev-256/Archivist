class _Column:
    def __init__(self, *args, **kwargs):
        pass

class _ForeignKey:
    def __init__(self, *args, **kwargs):
        pass

class _Relationship:
    def __init__(self, *args, **kwargs):
        pass

def relationship(*args, **kwargs):
    return _Relationship()

class SQLAlchemy:
    Model = object
    Column = _Column
    String = str
    Integer = int
    Float = float
    Text = str
    DateTime = str
    ForeignKey = _ForeignKey
    relationship = staticmethod(relationship)

    def __init__(self, *args, **kwargs):
        pass
    def init_app(self, app):
        pass

