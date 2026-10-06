#!/usr/bin/env python3
"""Fast static file server for the (multi-GB) localized ISO.

The stdlib ``http.server`` is single-threaded and copies file bytes through
Python, which caps a 3.86 GB download.  This server is threaded and hands the
payload to the kernel with ``os.sendfile`` (zero-copy), and it implements
``Range`` so download managers / resumable clients can pull in parallel.

    python3 tools/serve_iso.py [port] [directory]
"""
import os
import socket
import sys
from email.utils import formatdate
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else "build")
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 12000
BLOCK = 1 << 22  # 4 MiB sendfile chunks


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "iso-sendfile/1.0"

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _resolve(self):
        path = self.path.split("?", 1)[0]
        path = os.path.normpath(os.path.join(ROOT, path.lstrip("/")))
        if not path.startswith(ROOT) or not os.path.isfile(path):
            return None
        return path

    def _parse_range(self, size):
        rng = self.headers.get("Range")
        if not rng or not rng.startswith("bytes="):
            return None
        spec = rng[len("bytes="):].split(",")[0].strip()
        start_s, _, end_s = spec.partition("-")
        if start_s == "":  # suffix range: last N bytes
            n = int(end_s)
            return max(0, size - n), size - 1
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
        return start, min(end, size - 1)

    def _send(self, path, body):
        size = os.path.getsize(path)
        mtime = formatdate(os.path.getmtime(path), usegmt=True)
        rng = self._parse_range(size) if body else None
        fd = os.open(path, os.O_RDONLY)
        try:
            if rng:
                start, end = rng
                if start > end or start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", "bytes */%d" % size)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                self.send_response(206)
                self.send_header("Content-Range", "bytes %d-%d/%d" % (start, end, size))
                count = end - start + 1
            else:
                start, count = 0, size
                self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Last-Modified", mtime)
            self.send_header("Content-Length", str(count))
            self.end_headers()
            if not body:
                return
            sock = self.connection
            sent = 0
            while sent < count:
                try:
                    n = os.sendfile(sock.fileno(), fd, start + sent, count - sent)
                except (BlockingIOError, InterruptedError):
                    continue
                if n <= 0:
                    break
                sent += n
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            os.close(fd)

    def do_HEAD(self):
        path = self._resolve()
        if path is None:
            self.send_error(404)
            return
        self._send(path, body=False)

    def do_GET(self):
        path = self._resolve()
        if path is None:
            self.send_error(404)
            return
        self._send(path, body=True)


def main():
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    srv.daemon_threads = True
    srv.request_queue_size = 128
    print("serving %s on :%d" % (ROOT, PORT), flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
