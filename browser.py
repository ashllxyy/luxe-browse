import socket
import ssl
import os 
import html

MAX_REDIRECTS = 5

class URL:
    def __init__(self, url, redirects=0):
        if(redirects > MAX_REDIRECTS):
            raise ValueError("Exceeded maximum number of redirects - {} redirect(s)".format(MAX_REDIRECTS))
        
        if(redirects > 0):
            print("Redirect : ", redirects)
            
        self.redirects = redirects
        if(url[:5] == "data:"):
            self.scheme, url = url.split(":", 1)
            self.data_type, url = url.split(",", 1)
            self.body = url
            return
        
        self.scheme, url = url.split("://", 1)
        if("view-source" in self.scheme):
            self.scheme, self.scheme2 = self.scheme.split(":", 1) 
            self.view_source_url = self.scheme2 + "://" + url
            
        assert self.scheme in ["http", "https", "file", "view-source"]

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
            
        if self.scheme == "http" or self.scheme2 == "http":
            self.port = 80
        elif self.scheme == "https" or self.scheme2 == "https":
            self.port = 443
        
    def request(self):
        if self.scheme == "file":
            with open(self.path, "r") as f:
                return f.read()
        
        if self.scheme == "data":
            return self.body
                    
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
        
        if(int(status) >= 300 and int(status) <= 399):
            print("Redirecting to: ", response_headers["location"])
            if response_headers["location"].startswith("/"):
                return URL(self.scheme + "://" + self.host + response_headers["location"], self.redirects + 1).request()
            return URL(response_headers["location"], self.redirects + 1).request()
        
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
    if(url.scheme == "view-source"):
        print(html.unescape(body))
        return
    show_page(body)
            
if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))