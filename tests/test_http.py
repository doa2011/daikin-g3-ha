import unittest
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import msgpack
from daikin_g3.community import CommunityAdapter
from daikin_g3.protocol import ProtocolError, CommandError

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/msgpack")
        self.end_headers()
        self.wfile.write(msgpack.packb(data, use_bin_type=True))

    def authorized(self):
        if self.headers.get("Authorization") == "Basic YWRtaW46dGVzdA==":
            return True
        self.send_error(401)
        return False

    def do_GET(self):
        if not self.authorized():
            return
        if self.path == "/api/v1/capabilities":
            self.reply({"actions":["status.get","screen.page.set"]})
        elif self.path == "/api/v1/info":
            self.reply({"model":"BRY88BBA15G"})
        elif self.path == "/api/v1/status":
            self.reply({"online":True})
        else:
            self.send_error(404)

    def do_POST(self):
        if not self.authorized():
            return
        if self.path != "/api/v1/command" or self.headers.get_content_type() != "application/msgpack":
            self.send_error(400)
            return
        request = msgpack.unpackb(self.rfile.read(int(self.headers["Content-Length"])), raw=False)
        self.server.requests.append(request)
        code = "busy" if request["action"] == "busy.test" else "accepted"
        self.reply({"request_id": request["request_id"], "code":code, "data":{}})

class TestHTTP(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1",0),Handler)
        self.server.requests = []
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval":0.01}, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.server.server_port)
        self.adapter = CommunityAdapter(self.url,"test")
    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
    async def test_queries(self):
        self.assertEqual((await self.adapter.info())["model"],"BRY88BBA15G")
        self.assertEqual(await self.adapter.capabilities(),frozenset(("status.get","screen.page.set")))
        self.assertTrue((await self.adapter.status())["online"])
    async def test_command(self):
        result = await self.adapter.call("screen.page.set",{"direction":"next"})
        self.assertEqual(result["code"],"accepted")
        self.assertEqual(self.server.requests[0]["params"],{"direction":"next"})
        self.assertEqual(len(self.server.requests),1)
    async def test_busy_not_retried(self):
        with self.assertRaises(CommandError):
            await self.adapter.call("busy.test",{})
        self.assertEqual(len(self.server.requests),1)
    async def test_bad_password(self):
        from urllib.error import HTTPError
        with self.assertRaises(HTTPError) as error:
            await CommunityAdapter(self.url,"incorrect").info()
        self.assertEqual(error.exception.code,401)
