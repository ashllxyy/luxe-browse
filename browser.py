import socket
import ssl
import os 

class URL:
    def __init__(self, url):
        self.scheme, url = url.split("://", 1)        
        assert self.scheme in ["http", "https", "file"]

        if self.scheme == "file":
            self.path = url.replace("/", os.path.sep)
            self.host = None
            self.port = None
            return
        
        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url

        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
            
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443
        
    def request(self):
        if self.scheme == "file":
            with open(self.path, "r") as f:
                return f.read()
            
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        if(self.scheme == "https"):
            context = ssl.create_default_context()
            s = context.wrap_socket(s, server_hostname=self.host)
        
        s.connect((self.host, self.port))
        
        
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "luxe-ashllxyy"
            }
        for key, value in headers.items():
            request += "{}: {}\r\n".format(key, value)
        request += "\r\n"
        
        s.send(request.encode("utf8"))
        
        response = s.makefile("r", encoding="utf8", newline="\r\n")
        statusline = response.readline()
        version, status, explanation = statusline.split(" ", 2)
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()
        
        assert "transfer-encoding" not in response_headers
        assert "content-encoding" not in response_headers
        
        content = response.read()
        s.close()
        
        return content

def show_page(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif c == "&lt;":
            print("<", end="")
        elif c == "&gt;":
            print(">", end="")
        elif not in_tag:
            print(c, end="")
            
def load(url):
    body = url.request()
    show_page(body)
            
            
if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))