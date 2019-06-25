from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import re

from certbot.compat import os

import requests

class MockKongAdminHandler(BaseHTTPRequestHandler):
    CERTIFICATES_PATTERN = re.compile(r'/certificates')
    ROUTES_PATTERN = re.compile(r'/routes')
    THIS_DIR = os.path.dirname(os.path.abspath(__file__))

    def do_GET(self):
        content_len = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(content_len)

        self.request_info("GET", self.path, body)
        if re.search(self.CERTIFICATES_PATTERN, self.path):
            # Add response status code.
            self.send_response(200)

            # Add response headers.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

            # Add response content.
            filename = os.path.join(self.THIS_DIR, 
                "testdata/list_certificates.json")
 
            with open (filename, "r") as file:
                response_content = file.read()
            
            self.wfile.write(response_content.encode('utf-8'))
            return 
        elif re.search(self.ROUTES_PATTERN, self.path):
            # Add response status code.
            self.send_response(200)

            # Add response headers.
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()

            # Add response content.
            filename = os.path.join(self.THIS_DIR, 
                "testdata/list_routes.json")
 
            with open (filename, "r") as file:
                response_content = file.read()

            self.wfile.write(response_content.encode('utf-8'))
            return

    def do_POST(self):
        content_len = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(content_len)
        
        self.request_info("POST", self.path, body)

        self.response_content = '{"id":"new_cert"}'
        self.send_response(201)

        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(self.response_content.encode('utf-8'))

        return

    def do_PUT(self):
        content_len = int(self.headers.get('Content-Length'))
        body = self.rfile.read(content_len)
        
        self.request_info("PUT", self.path, body)

        self.response_content = '{"id":"new_cert"}'
        self.send_response(201)

        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(self.response_content.encode('utf-8'))

        return

    def do_PATCH(self):
        content_len = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(content_len)
        
        self.request_info("PATCH", self.path, body)

        self.response_content = '{"id":"updated_sni"}'
        self.send_response(200)

        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(self.response_content.encode('utf-8'))

        return

    def do_DELETE(self):
        content_len = int(self.headers.get('Content-Length',0))
        body = self.rfile.read(content_len)
        
        self.request_info("DELETE", self.path, body)

        self.send_response(204)

        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()

        self.wfile.write(''.encode('utf-8'))

        return

    def request_info(self, method, path, body):
        pass