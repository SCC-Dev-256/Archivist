class Flask:
    def __init__(self, *args, **kwargs):
        pass
    def route(self, *args, **kwargs):
        def decorator(f):
            return f
        return decorator
    def register_blueprint(self, *args, **kwargs):
        pass
    def run(self, *args, **kwargs):
        pass
class Blueprint:
    def __init__(self, *args, **kwargs):
        pass

def render_template(*args, **kwargs):
    return ""

def jsonify(*args, **kwargs):
    return {}

class Request:
    data = {}
request = Request()

def send_file(*args, **kwargs):
    pass


