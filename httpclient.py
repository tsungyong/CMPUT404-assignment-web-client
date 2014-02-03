#!/usr/bin/env python
# coding: utf-8
# Copyright 2013 Abram Hindle, Tsung Lin Yong
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib

def help():
    print "httpclient.py [GET/POST] [URL] [x-www-form-urlencoded POST data]\n"

class HTTPRequest(object):

    def __init__(self, code=200, head="", body=""):
        self.code = code
        self.head = head
        self.body = body

    def __str__(self):
        return "%s\r\n\r\n%s" % (self.head, self.body)

class HTTPClient(object):

    # Basically does what urlparse does
    def parseUrl(self, url):

        # [0] is hostname, [1] is port, [2] is path
        urlPattern = ("https?://((?:www)?.(?:\w|\.)+)"
                      "(?::(\d+))?((?:/(?:\w|/|.)+)?)")

        urlRegx = re.compile(urlPattern)
        parsedUrl = urlRegx.findall(url)

        hostAddress = parsedUrl[0][0]

        port = 80
        path = "/"

        if parsedUrl[0][1] != "":
            port = int(parsedUrl[0][1])

        if parsedUrl[0][2] != "":
            path = parsedUrl[0][2]

        return (hostAddress, port, path)

    def connect(self, host, port):

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, port))
        return s

    def get_code(self, data):
        
        httpCodePattern = "HTTP/1.[0|1] (\d\d\d)"
        httpCodeRegx = re.compile(httpCodePattern)

        httpCode = httpCodeRegx.findall(data)

        if httpCode:
            return int(httpCode[0])

        return None

    def get_headers(self,data):

        headerEndLocation = data.find("\r\n\r\n")
        if headerEndLocation != -1:
            return data[:headerEndLocation]
        return None

    def get_body(self, data):

        headerEndLocation = data.find("\r\n\r\n")
        if headerEndLocation != -1:
            return data[headerEndLocation+4:]

        return None

    # read everything from the socket
    def recvall(self, sock):

        contentLength = 0
        
        readingContent = False

        headerBuffer = bytearray()
        contentBuffer = bytearray()

        contentLengthRead = 0

        done = False
        while not done:
            part = sock.recv(1024)

            if not part:
                break

            # Note: this doesn't work if the content length line is split
            # between two sock.recvs
            contentLengthPattern = "Content-Length: (\d+)"
            contentLengthRegx = re.compile(contentLengthPattern)
            contentLengthMatch = contentLengthRegx.findall(part)

            if contentLengthMatch:
                contentLength = contentLengthMatch[0]
            
            headerEndLocation = part.find("\r\n\r\n")

            if headerEndLocation != -1:
                headerBuffer.extend(part[:headerEndLocation])
                contentBuffer.extend(part[headerEndLocation:])
                readingContent = True
                contentLengthRead = (contentLengthRead +
                                     len(part[headerEndLocation:]) - 4)
            elif readingContent:
                contentBuffer.extend(part)
                contentLengthRead = contentLengthRead + len(part)

                if contentLengthRead >= int(contentLength):
                    break

            else:
                headerBuffer.extend(part)
            
        return "%s%s" % (str(headerBuffer), str(contentBuffer))

    def GET(self, url, args=None):

        code = 500
        head = ""
        body = ""
        sock = None

        httpResponse = ""

        hostAddress = ""
        port = 80
        path = "/"

        hostAddress, port, path = self.parseUrl(url)

        try:
            sock = self.connect(hostAddress, port)
            sock.sendall("GET %s HTTP/1.1\r\nHost: %s\r\n\r\n" %
                         (path, hostAddress))
            httpResponse = self.recvall(sock)
        finally:
            if sock is not None:
                sock.close()

        code = self.get_code(httpResponse)
        head = self.get_headers(httpResponse)
        body = self.get_body(httpResponse)

        return HTTPRequest(code, head, body)

    def POST(self, url, args=None):
        code = 500
        head = ""
        body = ""
        sock = None

        httpResponse = ""

        hostAddress = ""
        port = 80
        path = "/"

        hostAddress, port, path = self.parseUrl(url)

        postArgsString = ""

        if args:
            postArgsString = args

        if isinstance(args, dict):
            postArgsString = urllib.urlencode(args)

        try:
            sock = self.connect(hostAddress, port)
            sock.sendall(("POST %s HTTP/1.1\r\n"
                          "Host: %s\r\n"
                          "Content-Type: application/x-www-form-urlencoded\r\n"
                          "Content-Length: %s\r\n\r\n"
                          "%s" %
                         (path, hostAddress, len(postArgsString),
                          postArgsString)))
            httpResponse = self.recvall(sock)
        finally:
            if sock is not None:
                sock.close()

        code = self.get_code(httpResponse)
        head = self.get_headers(httpResponse)
        body = self.get_body(httpResponse)

        return HTTPRequest(code, head, body)

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )
    
if __name__ == "__main__":
    client = HTTPClient()
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print client.command( sys.argv[2], sys.argv[1] )
    else:
        print client.command( sys.argv[2], sys.argv[1], sys.argv[3] )
