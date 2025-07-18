class Celery:
    def __init__(self, *args, **kwargs):
        self.control = type('Control', (), {'inspect': lambda self: type('I', (), {'active': lambda self: {}, 'reserved': lambda self: {}, 'scheduled': lambda self: {}, 'stats': lambda self: {}, 'ping': lambda self: {}})(), 'revoke': lambda self, *a, **k: None, 'purge': lambda self: None})()
        self.conf = type('Conf', (), {
            'update': lambda self, *a, **k: None,
            'beat_schedule': {}
        })()
        self.tasks = {}
    def task(self, *args, **kwargs):
        def decorator(func):
            def delay(*a, **k):
                return self.send_task(func.__name__, args=a, kwargs=k)
            func.delay = delay
            self.tasks[func.__name__] = func
            return func
        return decorator
    def send_task(self, *args, **kwargs):
        class Result:
            id = 'dummy'
        return Result()
    def AsyncResult(self, id):
        class Result:
            status = 'PENDING'
            info = {}
            result = None
            def failed(self):
                return False
            def successful(self):
                return False
        return Result()
celery = Celery()

class _Task:
    request = type('Req', (), {'id': 'dummy'})

current_task = _Task()







