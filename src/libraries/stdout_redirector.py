from tkinter.scrolledtext import ScrolledText
from threading import Thread
import tkinter as tk
import sys

from libraries.bettertk import BetterTk


class Buffer:
    __slots__ = ("buffer", )

    def __init__(self):
        self.buffer = ""

    def write(self, data:str) -> None:
        self.buffer += data

    def read(self) -> str:
        data, self.buffer = self.buffer, ""
        return data

    def flush(self) -> None:
        return None


class STDOUTRedirector:
    __slots__ = ("buffers", "root", "textbox", "running",
                 "old_stdout", "old_stderr", "on_close")

    def __init__(self, stdout:Buffer=None, stderr:Buffer=None,
                 stdout_kwargs:dict={}, stderr_kwargs:dict={}, **kwargs):
        self.buffers = (stdout, stderr)
        self.running = True
        self.on_close = None
        new_thread = Thread(target=self.set_up, daemon=True,
                            args=(stdout_kwargs, stderr_kwargs, kwargs))
        new_thread.start()

    def set_up(self, stdout_kwargs:dict, stderr_kwargs:dict, kwargs:dict) -> None:
        self.root = BetterTk()
        self.root.protocol("WM_DELETE_WINDOW", self.destroy)
        self.root.resizable(False, False)

        text_kwargs = dict(width=120, height=20, bg="black", fg="white",
                           highlightthickness=0, bd=0)
        text_kwargs.update(kwargs)
        self.textbox = ScrolledText(self.root, state="disabled", **text_kwargs)
        self.textbox.pack(fill="both", expand=True)

        _stderr_kwargs = dict(foreground="orange")
        _stderr_kwargs.update(stderr_kwargs)
        self.textbox.tag_config("stderr", **_stderr_kwargs)
        self.textbox.tag_config("stderr", **stdout_kwargs)

        clear_buton = tk.Button(self.root, text="Clear", command=self.clear,
                                activeforeground="white", fg="white",
                                activebackground="black", bg="black")
        clear_buton.pack(fill="x")

        self.root.after(100, self.flush)
        self.root.mainloop()

    def flush(self) -> None:
        if not self.running:
            return self.destroy()
        stdout, stderr = self.buffers
        stdout_data, stderr_data = "", ""
        if stdout is not None:
            stdout_data = stdout.read()
        if stderr is not None:
            stderr_data = stderr.read()

        self.textbox.config(state="normal")

        if len(stdout_data) + len(stderr_data) > 0:
            start, end = self.textbox.yview()
            see_end = (end == 1)
        else:
            see_end = False

        self.textbox.insert("end", stderr_data, ("stderr", ))
        self.textbox.insert("end", stdout_data, ("stdout", ))

        if see_end:
            self.textbox.see("end")

        self.textbox.config(state="disabled")

        self.root.after(100, self.flush)

    def clear(self) -> None:
        self.textbox.config(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.config(state="disabled")

    def start(self) -> None:
        stdout, stderr = self.buffers
        if stdout is not None:
            self.old_stdout = sys.stdout
            sys.stdout = stdout
        if stderr is not None:
            self.old_stderr = sys.stderr
            sys.stderr = stderr

    def stop(self) -> None:
        stdout, stderr = self.buffers
        if stdout is not None:
            sys.stdout = self.old_stdout
        if stderr is not None:
            sys.stderr = self.old_stderr

    def destroy(self) -> None:
        self.stop()
        if self.on_close is not None:
            self.on_close()
        self.root.destroy()
        del self.textbox
        del self.root


if __name__ == "__main__":
    from time import sleep
    import traceback

    new_stdout = Buffer()
    new_stderr = Buffer()

    redirector = STDOUTRedirector(new_stdout, new_stderr)
    redirector.start()
    redirector.on_close = lambda: print("Closing")

    print("Hello world")

    try:
        1/0
    except:
        traceback.print_exc()

    for i in range(100):
        print(f"Line number {i}")
        sleep(0.2)
    redirector.stop()
