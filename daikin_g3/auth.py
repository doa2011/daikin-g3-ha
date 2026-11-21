import base64

def auth_headers(password):
    if not password:
        return {}
    token = base64.b64encode(("admin:" + password).encode("utf-8")).decode("ascii")
    return {"Authorization": "Basic " + token}
