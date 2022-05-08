from http.server import HTTPServer, BaseHTTPRequestHandler
from http import HTTPStatus
import json
import time
import logging
from Main import *

#HostName = "localhost"
HostName = "192.168.137.51"
ServerPort = 8888
manager = Manager()

class PostRequestData(object):
    def __init__(self, data):
        self.__dict__ = json.loads(data)

class Server(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(HTTPStatus.OK.value)
        self.send_header('Content-type', 'application/json')        
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

    def do_GET(self):
        self._set_headers()
        self.wfile.write(json.dumps({"testing": True}).encode('utf-8'))
        
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        print("POST request received:\n%s\n" % (post_data.decode('utf-8')))
        result = execute(post_data)
        self._set_headers()
        self.wfile.write(json.dumps(result).encode('utf-8'))

def execute(request):
    requestData = PostRequestData(request)
    h = Handler()
    responseData = h.handle_request(manager, requestData)
    del h
    return responseData

def run_server():
    server_address = (HostName, ServerPort)
    webServer = HTTPServer(server_address, Server)
    print("Server started http://%s:%s" % (server_address))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()
    print("Server stopped.")


if __name__ == '__main__':
    run_server()