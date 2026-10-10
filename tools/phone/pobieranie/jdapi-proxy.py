#!/usr/bin/python3
# SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
# SPDX-License-Identifier: MIT
#
# Unix socket in front of the JDownloader 2 local API (127.0.0.1:3128).
#
# JD2's "deprecated" API takes plain GET requests without any authentication,
# so any web page open in the phone's browser could call it (CSRF). The
# firewall (jdapi-firewall.service) therefore lets only sockets of the group
# jdapi reach port 3128; this proxy runs with that group and serves
# /run/jdapi/jdapi.sock, which only the phone user can open. The Pobieranie
# app talks to the socket, web content cannot reach unix sockets at all.
#
# One request per connection, HTTP/1.0: "GET /namespace/method?params".

import http.client
import os
import re
import socketserver

SOCKET = "/run/jdapi/jdapi.sock"
PATH_OK = re.compile(r"^/[A-Za-z0-9_]+/[A-Za-z0-9_]+(\?[A-Za-z0-9%._~&!*'()+,;=:@/-]*)?$")


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        line = self.rfile.readline(65536).decode("latin-1").strip()
        parts = line.split(" ")
        # read and drop the request headers
        while self.rfile.readline(8192).strip():
            pass
        if len(parts) < 2 or parts[0] != "GET" or not PATH_OK.match(parts[1]):
            self.reply(400, b'{"type":"BAD_REQUEST"}')
            return
        try:
            conn = http.client.HTTPConnection("127.0.0.1", 3128, timeout=60)
            conn.request("GET", parts[1])
            r = conn.getresponse()
            self.reply(r.status, r.read())
            conn.close()
        except OSError as e:
            self.reply(503, ('{"type":"OFFLINE","message":"%s"}' % type(e).__name__).encode())

    def reply(self, status, body):
        head = "HTTP/1.0 %d X\r\nContent-Type: application/json\r\nContent-Length: %d\r\n\r\n" % (status, len(body))
        self.wfile.write(head.encode() + body)


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True


if __name__ == "__main__":
    if os.path.exists(SOCKET):
        os.unlink(SOCKET)
    old = os.umask(0o177)  # socket 0600, owner = the phone user
    srv = Server(SOCKET, Handler)
    os.umask(old)
    srv.serve_forever()
