import sys


# Connection: close
HTTP_HEADER = """
HTTP/1.1 200 OK
Content-Type: {mimetype}; utf-8
Accept-Ranges: bytes
Content-Length: {file_length}
Connection: keep-alive
Cache-Control: no-cache
X-Content-Type-Options: nosniff

"""[1:].replace("\n", "\r\n")


EXTENSION_MIMETYPE = {
                      # Videos
                      "mp4":  "video/mp4",
                      "ts":   "video/mp2t",
                      "avi":  "video/x-msvideo",
                      "mpeg": "video/mpeg",
                      # Audio
                      "mp3":  "audio/mpeg",
                      "wav":  "audio/wav",
                      # Images:
                      "ico":  "image/icon",
                      "png":  "image/png",
                      "svg":  "image/svg+xml",
                      "gif":  "image/gif",
                      "jpg":  "image/jpeg",
                      "jpeg": "image/jpeg",
                      "bmp":  "image/bmp",
                      # Fonts:
                      "ttf":  "font/ttf",
                      "otf":  "font/otf",
                      # Archives:
                      "bz":   "application/x-bzip",
                      "bz2":  "application/x-bzip2",
                      "gz":   "application/gzip",
                      "rar":  "application/vnd.rar",
                      "zip":  "application/zip",
                      "tar":  "application/x-tar",
                      "7z":   "application/x-7z-compressed",
                      # Text:
                      "txt":  "text/plain",
                      "html": "text/html",
                      "htm":  "text/html",
                      "css":  "text/css",
                      "js":   "text/javascript",
                      "mjs":  "text/javascript",
                      "php":  "application/x-httpd-php",
                      "py":   "text/x-python",
                      # Other
                      "pyc":  "application/x-python-code",
                      "pyd":  "application/x-python-code",
                      "pyo":  "application/x-python-code",
                      "doc":  "application/msword",
                      "epub": "application/epub+zip",
                      "jar":  "application/java-archive",
                      "json": "application/json",
                      "pdf":  "application/pdf",
                      "swf":  "application/x-shockwave-flash",
                      # Default:
                      "*":    "application/octet-stream"
                     }
EXTENSION_MIMETYPE["ts"] = EXTENSION_MIMETYPE["*"]


class HTTPResponse:
    __slots__ = ("data", "mimetype", "file_length")
    def __init__(self, file_length:int=None, mimetype:str=None, data:bytes=b""):
        if mimetype is None:
            mimetype = EXTENSION_MIMETYPE["*"]

        self.mimetype = mimetype
        self.data = data
        self.file_length = file_length

    def mimetype_from_extension(self, extension:str) -> None:
        if extension in EXTENSION_MIMETYPE:
            self.mimetype = EXTENSION_MIMETYPE[extension]
        else:
            self.mimetype = EXTENSION_MIMETYPE["*"]
    set_extension = mimetype_from_extension

    def to_bytes(self) -> bytes:
        body = self.get_body()
        return self.get_header(file_length=len(body)) + body
    __bytes__ = to_bytes

    def get_header(self, file_length:int) -> bytes:
        if self.file_length is not None:
            file_length = self.file_length
        return HTTP_HEADER.format(mimetype=self.mimetype,
                                  file_length=file_length).encode()

    def get_body(self) -> bytes:
        return self.data


class JSCode:
    __slots__ = ("mode", )

    def __init__(self, mode:int):
        self.mode = mode

    def to_bytes(self) -> bytes:
        return self.to_string().replace("\n", "\r\n").encode()
    __bytes__ = to_bytes

    def format(self, **kwargs):
        output = {}
        if self.mode & 1:
            output.update({"GOTO_JS": GOTO_JS.format(**kwargs)})
        if self.mode & 2:
            output.update({"GOBACK_JS": GOBACK_JS.format(**kwargs)})
        if self.mode & 4:
            output.update({"DOWNLOAD_TS_JS": DOWNLOAD_TS_JS.format(**kwargs)})
        return output

    def all(self) -> dict:
        return dict(GOTO_JS=GOTO_JS,
                    GOBACK_JS=GOBACK_JS,
                    DOWNLOAD_TS_JS=DOWNLOAD_TS_JS)

    def to_string(self) -> str:
        text = ""
        if self.mode & 1:
            text += GOTO_JS
        if self.mode & 2:
            text += GOBACK_JS
        if self.mode & 4:
            text += DOWNLOAD_TS_JS
            raise NotImplementedError("Hmmm. Passing `filename` to `JSCode`?")
        return text
    __str__ = to_string


class HTMLCode:
    __slots__ = ("website", )

    def __init__(self, website:str):
        self.website = website.lower()

    def __repr__(self) -> str:
        return f"HTMLCode({self.website})"

    def to_string(self, **kwargs) -> str:
        return self.construct_website(**kwargs)

    def to_bytes(self, **kwargs) -> bytes:
        return self.to_string(**kwargs).encode()

    def to_http(self, **kwargs) -> bytes:
        data = self.to_bytes(**kwargs)
        response = HTTPResponse(data=data)
        response.set_extension("html")
        return response.to_bytes()

    def construct_website(self, **kwargs) -> str:
        if self.website == "folder":
            full_text = HTML_FOLDER
            # The start of the HTML
            text = full_text[0]
            # The files listed
            for file in kwargs["files"]:
                text += "\n        "
                text += f"<a href=\"\"/ onclick=\"return goto('{file}')\">" \
                        f"{file}</a><p></p>"
            # The end of the HTML
            text += full_text[1]
            return text.format(**JSCode(3).format(**kwargs), **kwargs)

        if self.website == "404":
            return HTML_404.format(**JSCode(2).format(**kwargs), **kwargs)

        if self.website == "play ts":
            return HTML_PLAY_TS_FILE.format(**JSCode(6).format(**kwargs),
                                            **kwargs)

        if self.website == "error":
            return HTML_ERROR.format(**JSCode(2).format(**kwargs), **kwargs)

        if self.website == "play mp4":
            return HTML_MP4.format(**JSCode(2).format(**kwargs), **kwargs)

        if self.website == "raw":
            return kwargs["html"]

        raise RuntimeError("Unknown type of website.")


# All of the JS code:
GOTO_JS = """
function goto(filename){{
    let path = window.location.pathname;
    if (path === "/"){{
        path = "";
    }}
    window.location.assign(path+"/"+filename);
    return false;
}}
"""
GOBACK_JS = """
function goback(){{
    let path = window.location.pathname;
    if (path === "/"){{
        return false;
    }}
    path = path.substr(0, path.lastIndexOf("/"));
    if (path === ""){{
        path = "/";
    }}
    window.location.assign(path);
    return false;
}}
"""
DOWNLOAD_TS_JS = """
function download_file(){{
    document.getElementById("download_iframe").src = "{filename}.ts"
    return false
}}
"""


# All of the HTML templates:
HTML_FOLDER = ("""
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>200</title>
        <script>
{GOBACK_JS}
{GOTO_JS}
        </script>
    </head>

    <body>"""[1:],  """
        <p>Click <a href="" onclick="return goback()">here</a> to go back</p>
    </body>
</html>
""")

HTML_404 = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>404</title>
        <script>
{GOBACK_JS}
        </script>
    </head>

    <body>
        <p>File: "{filename}" doesn't exist.</p>
        <p>Click <a href="" onclick="return goback()">here</a> to go back</p>
    </body>
</html>
"""[1:]

HTML_PLAY_TS_FILE = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>200</title>
        <script>
{DOWNLOAD_TS_JS}
{GOBACK_JS}
        </script>
    </head>
    <body>
        <p>Click <a href="" onclick="return download_file()">here</a> to download "{filename}".</p>
        <p>Click <a href="" onclick="return goback()">here</a> to go back</p>
        <iframe id="download_iframe" style="display:none;" title="downloaded"></iframe>
    </body>
</html>
"""

HTML_ERROR = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>200</title>
    </head>
    <body>
        <pre>{error}</pre>
        <p></p><p></p><p></p>
        <pre>{traceback}</pre>
    </body>
</html>
"""[1:]

HTML_MP4 = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>200</title>
        <script>
{GOBACK_JS}
        </script>
    </head>
    <body>
        <p>Playing: {filename}</p>
        <video id="video_player" src="{filename}.mp4" type="video/mp4" controls></video>
        <p>Click <a href="" onclick="return goback()">here</a> to go back</p>
    </body>
</html>
"""[1:]


def response_from_mp2t(data:bytes, length:int=None) -> bytes:
    if length is None:
        length = len(data)
    response = HTTPResponse(file_length=length, data=data)
    response.set_extension("ts")
    return response.to_bytes()

def response_from_mp4(data:bytes, length:int=None) -> bytes:
    if length is None:
        length = len(data)
    response = HTTPResponse(file_length=length, data=data)
    response.set_extension("mp4")
    return response.to_bytes()

def txt(text:bytes, length:int=None) -> bytes:
    if length is None:
        length = len(data)
    response = HTTPResponse(file_length=length, data=text)
    response.set_extension("txt")
    return response.to_bytes()

def raw_html(html:str) -> bytes:
    return HTMLCode("raw").to_http(html=html)

def get_404(filename:str) -> bytes:
    filename = filename.replace("\\", "/").split("/")[-1]
    return HTMLCode("404").to_http(filename=filename)

def play_ts_file(filename:str) -> bytes:
    filename = filename.replace("\\", "/").split("/")[-1]
    return HTMLCode("play ts").to_http(filename=filename)

def get_favicon() -> bytes:
    response = HTTPResponse(file_length=0)
    response.set_extension("ico")
    return response.to_bytes().replace(b"200 OK", b"404 Not Found")

def folder(files:(str, ...)) -> bytes:
    files = tuple(file.replace("\\", "/") for file in files)
    return HTMLCode("folder").to_http(files=files)

def error(error:Exception, traceback:str) -> bytes:
    error = repr(error).replace("'", "\"")\
                       .replace("{", "{{")\
                       .replace("}", "}}")\
                       .replace("\\", "\\\\")

    traceback = traceback.replace("{", "{{")\
                         .replace("}", "}}")\
                         .replace("\\", "\\\\")

    return HTMLCode("error").to_http(error=error, traceback=traceback)

def play_mp4_file(filename:str) -> bytes:
    filename = filename.replace("\\", "/").split("/")[-1]
    return HTMLCode("play mp4").to_http(filename=filename)
