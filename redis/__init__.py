class DummyConn:
    def ping(self):
        return True

def from_url(*args, **kwargs):
    return DummyConn()

