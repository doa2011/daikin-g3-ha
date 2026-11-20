import msgpack
import uuid

class ProtocolError(Exception):
    pass

class CommandError(ProtocolError):
    def __init__(self, code):
        self.code = code
        super().__init__(str(code))

def encode_command(action, params, request_id=None):
    request_id = request_id or uuid.uuid4().hex
    return request_id, msgpack.packb({"request_id":request_id,"action":action,"params":params}, use_bin_type=True)

def decode_object(body):
    try:
        value = msgpack.unpackb(body, raw=False)
    except (ValueError, TypeError) as exc:
        raise ProtocolError("invalid MessagePack") from exc
    if not isinstance(value, dict):
        raise ProtocolError("expected map")
    return value

def decode_result(body, request_id):
    result = decode_object(body)
    if result.get("request_id") != request_id:
        raise ProtocolError("request ID mismatch")
    if result.get("code") not in ("ok", "accepted"):
        raise CommandError(result.get("code"))
    return result
