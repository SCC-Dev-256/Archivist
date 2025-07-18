class Response:
    def __init__(self, status_code=200, text=""):
        self.status_code = status_code
        self.text = text

class Session:
    def get(self, *args, **kwargs):
        return Response()
    def post(self, *args, **kwargs):
        return Response()

class exceptions:
    class Timeout(Exception):
        pass

def get(*args, **kwargs):
    return Response()

def post(*args, **kwargs):
    return Response()

