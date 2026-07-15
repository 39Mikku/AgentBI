from __future__ import annotations

import threading
from pathlib import Path


class NativeDirectoryPicker:
    def __init__(self):
        self._lock = threading.Lock()

    def choose(self, title: str, initial_directory: str | None = None) -> str | None:
        from tkinter import Tk, filedialog

        with self._lock:
            root = Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            root.update_idletasks()
            options: dict[str, object] = {"title": title, "mustexist": True, "parent": root}
            if initial_directory:
                candidate = Path(initial_directory).expanduser()
                if candidate.exists() and candidate.is_dir():
                    options["initialdir"] = str(candidate)
            try:
                selected = filedialog.askdirectory(**options)
                return str(Path(selected).resolve()) if selected else None
            finally:
                root.destroy()

