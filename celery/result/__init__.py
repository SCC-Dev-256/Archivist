class AsyncResult:
    def __init__(self, id, app=None):
        self.id = id
        self.status = 'PENDING'
        self.info = {}
        self.result = None
    def failed(self):
        return False
    def successful(self):
        return False

