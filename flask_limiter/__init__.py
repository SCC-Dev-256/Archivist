class Limiter:
    def __init__(self, *args, **kwargs):
        pass
    def limit(self, *args, **kwargs):
        def decorator(func):
            return func
        return decorator

