from urllib.parse import unquote
from threading import Thread
from time import sleep
import importlib
import traceback
import os.path
import socket
import sys

from libraries import website_pages

socket.Socket = socket.socket


GUI = False


ERROR_RAISED = False
CHUNK_SIZE = 1024*1024*10


class FTPServer:
    __slots__ = ("port", "ip", "socket", "running")

    def __init__(self, port:int=80):
        self.port = port
        self.running = True
        self.ip = socket.gethostbyname(socket.gethostname())

        sys.stderr.write(f"IP address = {self.ip}\n")
        sys.stderr.write(f"port = {self.port}\n")

        self.socket = socket.Socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("0.0.0.0", self.port))
        self.socket.listen()

    def send_exception(self, connection:socket.Socket, error:Exception) -> None:
        _traceback = traceback.format_exc()
        self.sendall(connection, website_pages.error(error, _traceback))

    def __del__(self) -> None:
        self.stop()

    def start_server(self) -> None:
        new_thread = Thread(target=self._start_server, daemon=True)
        new_thread.start()

    def _start_server(self) -> None:
        while self.running:
            try:
                connection, address = self.socket.accept()
                new_thread = Thread(target=self.handle_connection,
                                    daemon=True, args=(connection, ))
                new_thread.start()
            except OSError:
                self.running = False

    def handle_connection(self, connection:socket.Socket) -> None:
        connection_id = str(id(connection))[-5:]
        request = connection.recv(1024).decode()
        importlib.reload(website_pages)

        if ("GET " not in request) or (" HTTP" not in request):
            connection.close()
            return None

        sys.stderr.write(f"[Debug]: Connection({connection_id}) opened.\n")

        filename = request[request.index("GET ")+5:request.index(" HTTP")]
        filename = unquote(filename) # "%20" => " "

        if len(filename) == 0:
            filename = "."
        print(f"[Debug]: \t\tAsked for \"{filename}\"")

        # Make sure we don't leak any files:
        if (".." in filename) or (":" in filename):
            print("[WARNING]: \tSomeone tried to leak files.")
            self.sendall(connection, website_pages.get_404(filename))

        # Send "favicon.ico", don't have a good icon right now
        elif filename == "favicon.ico":
            self.sendall(connection, website_pages.get_favicon())

        # If the file exists:
        elif os.path.exists(filename):
            if os.path.isdir(filename):
                self.send_folder(connection, filename)
            else:
                self.send_file(connection, filename)

        # Unknown file
        else:
            print("[Debug]: \t\tSending 404")
            self.sendall(connection, website_pages.get_404(filename))

        # Close the connection:
        print(f"[Debug]: \t\tConnection({connection_id}) closed.")
        connection.close()

    def send_file(self, connection:socket.Socket, filename:str) -> None:
        # Get the file's extenstion
        extension = filename.split(".")[-1]
        if "/" in extension.replace("\\", "/"):
            extension = ""

        # Read the file and get the filesize:
        size = os.path.getsize(filename)
        file = open(filename, "rb")
        data = file.read(CHUNK_SIZE)

        # Check if we should send it as bytes or as plain text
        try:
            data.decode()
            send_as_bytes = False
        except UnicodeDecodeError:
            send_as_bytes = True

        # If it's a htm/html file
        if (extension in ("html", "htm")) and (not send_as_bytes):
            data += file.read()
            file.close()
            data = data.decode()
            self.sendall(connection, website_pages.raw_html(data))
            return None

        # Send the headers + first chunk
        if not send_as_bytes:
            self.sendall(connection, website_pages.txt(data, size))
        elif extension == "mp4":
            self.sendall(connection, website_pages.response_from_mp4(data, size))
        else:
            self.sendall(connection, website_pages.response_from_mp2t(data, size))

        # Send the rest of the data
        self.send_from_buffer(connection, file)

    def send_from_buffer(self, connection:socket.Socket, file) -> None:
        try:
            data = b"Please stop looking at my code"
            while len(data) != 0:
                data = file.read(CHUNK_SIZE)
                self.sendall(connection, data)
        finally:
            file.close()

    def send_folder(self, connection:socket.Socket, folder:str) -> None:
        print("[Debug]: \t\tSending the contents of the folder.")
        all_files = (file for file in os.listdir(folder) if os.path.isfile(os.path.join(folder, file)))
        filtered_files = []
        for file in all_files:
            if file[-4:] == ".mp4":
                file = file[:-4]
            filtered_files.append(file)
        ordered_files = tuple(sorted(sorted(filtered_files), key=len))
        folders = tuple(file for file in os.listdir(folder) if not os.path.isfile(os.path.join(folder, file)))
        all = tuple(sorted(sorted(folders), key=len)) + ordered_files

        with open(".ignore", "r") as file:
            ignored_files = file.read().split("\n")
        all_with_ignore = []

        for filename in all:
            path = filename.replace("\\", "/")
            if folder != ".":
                path = (folder+"/"+filename)
            if path not in ignored_files:
                all_with_ignore.append(filename)

        self.sendall(connection, website_pages.folder(tuple(all_with_ignore)))

    def sendall(self, connection:socket.Socket, data:bytes) -> None:
        try:
            connection.sendall(data)
        except ConnectionAbortedError:
            return None
        except ConnectionResetError:
            return None

    def stop(self) -> None:
        if not self.running:
            return None
        self.running = False
        self.socket.close()
        sys.stderr.write("Stopped server.\n")


def main_gui() -> None:
    global server, redirector
    from libraries import stdout_redirector
    new_stdout = stdout_redirector.Buffer()
    new_stderr = stdout_redirector.Buffer()
    stderr_kwargs = dict(foreground="red")
    redirector = stdout_redirector.STDOUTRedirector(new_stdout, new_stderr,
                                                    stderr_kwargs=stderr_kwargs,
                                                    width=100, height=20)
    redirector.start()

    server = FTPServer()
    server.start_server()

    redirector.on_close = server.stop
    sleep(0.2)
    redirector.root.title("Hoster")

    try:
        while server.running:
            sleep(0.2)
    except KeyboardInterrupt:
        server.stop()
        sys.stderr.write("KeyboardInterrupt\n")

    # Make sure server fully stops
    sleep(0.2)

    if not ERROR_RAISED:
        redirector.stop()

    # Make sure tkinter exits correctly
    sleep(0.2)

def main() -> None:
    global server
    print("Press `Ctrl-C` to stop the server.")
    server = FTPServer()
    server.start_server()

    try:
        while server.running:
            sleep(0.2)
    except KeyboardInterrupt:
        server.stop()
        sys.stderr.write("KeyboardInterrupt\n")


if __name__ == "__main__":
    if GUI:
        main_gui()
    else:
        main()
