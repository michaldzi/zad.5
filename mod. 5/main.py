import os
import json
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse, unquote_plus
from datetime import datetime
import pathlib
import mimetypes

DATA_FILE = "storage/data.json"
UDP_PORT = 5000


if not os.path.exists("storage"):
    os.makedirs("storage")


if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)


class HttpHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        data = self.rfile.read(int(self.headers["Content-Length"]))
        data_parse = unquote_plus(data.decode())
        data_dict = {
            key: value for key, value in [el.split("=") for el in data_parse.split("&")]
        }

        self.send_response(302)
        self.send_header("Location", "/")
        self.end_headers()

        self.send_to_udp_server(data_dict)

    def send_to_udp_server(self, data):
        message = json.dumps(data).encode("utf-8")
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(message, ("localhost", UDP_PORT))

    def do_GET(self):
        pr_url = urlparse(self.path)
        if pr_url.path == "/":
            self.send_html_file("index.html")
        elif pr_url.path == "/message":
            self.send_html_file("message.html")
        else:
            if pathlib.Path().joinpath(pr_url.path[1:]).exists():
                self.send_static()
            else:
                self.send_html_file("error.html", 404)

    def send_html_file(self, filename, status=200):
        self.send_response(status)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "rb") as fd:
            self.wfile.write(fd.read())

    def send_static(self):
        self.send_response(200)
        mt = mimetypes.guess_type(self.path)
        if mt:
            self.send_header("Content-type", mt[0])
        else:
            self.send_header("Content-type", "text/plain")
        self.end_headers()
        with open(f".{self.path}", "rb") as file:
            self.wfile.write(file.read())


class UDPServer(threading.Thread):
    def __init__(self, host="localhost", port=UDP_PORT):
        super().__init__()
        self.host = host
        self.port = port

    def run(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.host, self.port))
            while True:
                data, _ = sock.recvfrom(4096)
                message = json.loads(data.decode("utf-8"))
                self.save_message(message)

    def save_message(self, data):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        with open(DATA_FILE, "r") as f:
            json_data = json.load(f)

        json_data[timestamp] = data

        with open(DATA_FILE, "w") as f:
            json.dump(json_data, f, indent=4)


def run_http_server():
    server_address = ("", 3000)
    http = HTTPServer(server_address, HttpHandler)
    print("HTTP server running on port 3000")
    try:
        http.serve_forever()
    except KeyboardInterrupt:
        http.server_close()


if __name__ == "__main__":
    udp_server = UDPServer()
    udp_server.start()

    http_thread = threading.Thread(target=run_http_server)
    http_thread.start()
