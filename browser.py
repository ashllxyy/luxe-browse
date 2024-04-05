import socket
import ssl
import os 
import html
import tkinter

WIDTH, HEIGHT = 800, 600
MAX_REDIRECTS = 5
HSTEP, VSTEP = 8, 18

def layout(text):
    display_list = []
    cursor_x, cursor_y = HSTEP, VSTEP
    for c in text:
        if c == "\n":
            cursor_y += VSTEP
            cursor_x = HSTEP
            continue
        display_list.append((cursor_x, cursor_y, c))
        cursor_x += HSTEP
        if cursor_x >= WIDTH - HSTEP:
            cursor_y += VSTEP
            cursor_x = HSTEP
    return display_list

class Browser:
    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window, 
            width=WIDTH,
            height=HEIGHT
        )
        self.scroll = 0
        
        self.canvas.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        
        # Binds
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.mouse_scroll)
        self.window.bind("<Configure>", self.resize)
        
    def load(self, url):
        body = url.request()
        self.text = lex(body)
        self.display_list = layout(self.text)
        self.draw()
    
    def draw(self):
        self.canvas.delete("all")
        for x, y, c in self.display_list:
            if y > self.scroll + HEIGHT: continue
            if y + VSTEP < self.scroll: continue
            self.canvas.create_text(x, y - self.scroll, text=c)
    
    def scrolldown(self, event):
        self.scroll += VSTEP
        self.canvas.delete("all")
        self.draw()
        
    def scrollup(self, event):
        if(self.scroll == 0): return
        self.scroll -= VSTEP
        self.canvas.delete("all")
        self.draw()
        
    def mouse_scroll(self, event):
        if(event.delta > 0):
            self.scrollup(event)
        else:
            self.scrolldown(event)

    def resize(self, event):
        global WIDTH, HEIGHT
        WIDTH, HEIGHT = event.width, event.height
        self.display_list = layout(self.text)
        self.canvas.pack(fill=tkinter.BOTH, expand=tkinter.YES)
        self.draw()
        
class URL:
    def __init__(self, url, redirects=0):
        self.socket = None
        self.view_source_url = None
        
        if(redirects > MAX_REDIRECTS):
            raise ValueError("Exceeded maximum number of redirects - {} redirect(s)".format(MAX_REDIRECTS))
        
        if(redirects > 0):
            print("Redirect : ", redirects)
            
        self.redirects = redirects
        
        try:
            if(url[:5] == "data:"):
                self.scheme, url = url.split(":", 1)
                self.data_type, url = url.split(",", 1)
                self.body = url
                return
            
            self.scheme, url = url.split("://", 1)
            if("view-source" in self.scheme):
                self.scheme, scheme = self.scheme.split(":", 1) 
                self.view_source_url = scheme + "://" + url
                
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
                
            if self.scheme == "http":
                self.port = 80
            elif self.scheme == "https":
                self.port = 443

            if(self.view_source_url):
                view_source_scheme = self.view_source_url.split("://", 1)[0]
                if(view_source_scheme == "http"):
                    self.port = 80
                elif(view_source_scheme == "https"):
                    self.port = 443
        except Exception as e:
            self.malformed = True
            self.scheme = "about"
            self.host = "blank"
            self.path = ""
            self.port = None
            self.body = ""            
                
    def connect(self):
        if self.socket is None:
            self.socket = socket.socket(
                family=socket.AF_INET,
                type=socket.SOCK_STREAM,
                proto=socket.IPPROTO_TCP,
            )
            if self.scheme == "https":
                context = ssl.create_default_context()
                self.socket = context.wrap_socket(self.socket, server_hostname=self.host)
            self.socket.connect((self.host, self.port))

    def close(self):
        if self.socket is not None:
            self.socket.close()
            self.socket = None
    
    def request(self):
        if self.scheme == "file":
            with open(self.path, "r") as f:
                return f.read()
        
        if self.scheme == "data":
            return self.body
        
        if self.malformed:
            return self.body
        
        self.connect()
        
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        
        headers = {
            "Host": self.host,
            "Connection": "close",
            "User-Agent": "luxe-ashllxyy"
            }
        for key, value in headers.items():
            request += "{}: {}\r\n".format(key, value)
        request += "\r\n"
        
        self.socket.send(request.encode("utf8"))
        
        response = self.socket.makefile("r", encoding="utf8", newline="\r\n")
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
        
        content_length = int(response_headers.get("content-length", 0))
        
        if content_length > 0:
            content = response.read(content_length)
        else:
            content = response.read()
        
        if(headers["Connection"] == "close"):
            self.socket.close()
            
        return content

def lex(body):
    text = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif c == "&lt;":
            text += "<"
        elif c == "&gt;":
            text += ">"
        elif not in_tag:
            text += c
    return text
            
def load(url):
    body = url.request()
    if(url.scheme == "view-source"):
        print(html.unescape(body))
        return
    lex(body)

test_urls = ["http://example.com", "https://example.com", "http://example.com:8080", "https://example.com:8080", "data:text/plain,Hello%2C%20World!", "view-source:http://example.com"]

if __name__ == "__main__":
    import sys
    arg = sys.argv[1]
    if arg == "test":
        for url in test_urls:
            print("URL: ", url)
            load(URL(url))
    else:
        Browser().load(URL(sys.argv[1]))
        tkinter.mainloop()