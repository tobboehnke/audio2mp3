"""
audio2mp3 — Einfacher Audio-Konverter mit Drag & Drop
Für Windows: als .exe gebaut via PyInstaller (ffmpeg eingebettet)
"""
import os
import sys
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path


# ffmpeg-Pfad: im selben Ordner wie die .exe (PyInstaller packt es dort rein)
def get_ffmpeg():
    if getattr(sys, "frozen", False):
        # Läuft als .exe (PyInstaller)
        base = Path(sys._MEIPASS)
    else:
        # Läuft als .py Script
        base = Path(__file__).parent
    
    ffmpeg = base / "ffmpeg.exe" if sys.platform == "win32" else base / "ffmpeg"
    if ffmpeg.exists():
        return str(ffmpeg)
    
    # Fallback: System-ffmpeg
    import shutil
    return shutil.which("ffmpeg") or str(ffmpeg)


SUPPORTED = {".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma", ".mp4", ".webm"}
FFMPEG = get_ffmpeg()


def convert_file(input_path: Path, bitrate: str, log_callback, done_callback):
    """Konvertiert eine Datei zu MP3 — läuft in eigenem Thread."""
    output_path = input_path.with_suffix(".mp3")
    
    cmd = [
        FFMPEG,
        "-i", str(input_path),
        "-vn", "-ar", "44100", "-ac", "2",
        "-b:a", bitrate,
        "-f", "mp3", "-y",
        str(output_path),
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode == 0:
            size = output_path.stat().st_size / 1024 / 1024
            log_callback(f"✅  {input_path.name}  →  {output_path.name}  ({size:.1f} MB)", "ok")
            done_callback(True)
        else:
            # Letzten relevanten Fehler aus stderr holen
            lines = [l for l in result.stderr.split("\n") if l.strip()]
            err = lines[-1] if lines else "Unbekannter Fehler"
            log_callback(f"❌  {input_path.name}:  {err}", "err")
            done_callback(False)
    except subprocess.TimeoutExpired:
        log_callback(f"❌  {input_path.name}: Timeout (Datei zu groß?)", "err")
        done_callback(False)
    except Exception as e:
        log_callback(f"❌  {input_path.name}: {e}", "err")
        done_callback(False)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("audio2mp3")
        self.geometry("600x480")
        self.minsize(500, 400)
        self.configure(bg="#1e1e2e")
        self.resizable(True, True)
        
        self._queue = []
        self._running = 0
        self._success = 0
        self._failed = 0
        
        self._build_ui()
        self._setup_dnd()

    def _build_ui(self):
        # Titel
        tk.Label(
            self, text="🎵  audio2mp3", font=("Segoe UI", 18, "bold"),
            bg="#1e1e2e", fg="#cdd6f4"
        ).pack(pady=(20, 4))
        
        tk.Label(
            self, text="Audiodateien in MP3 umwandeln",
            font=("Segoe UI", 10), bg="#1e1e2e", fg="#a6adc8"
        ).pack(pady=(0, 16))

        # Drop-Zone
        self.drop_frame = tk.Frame(
            self, bg="#313244", bd=0, highlightthickness=2,
            highlightbackground="#585b70", highlightcolor="#89b4fa",
            cursor="hand2"
        )
        self.drop_frame.pack(fill="x", padx=24, pady=4)
        
        self.drop_label = tk.Label(
            self.drop_frame,
            text="📂  Dateien hierher ziehen\noder klicken zum Auswählen",
            font=("Segoe UI", 12), bg="#313244", fg="#89b4fa",
            pady=28, cursor="hand2"
        )
        self.drop_label.pack(fill="x")
        
        self.drop_frame.bind("<Button-1>", lambda e: self._pick_files())
        self.drop_label.bind("<Button-1>", lambda e: self._pick_files())
        self.drop_frame.bind("<Enter>", lambda e: self.drop_frame.configure(highlightbackground="#89b4fa"))
        self.drop_frame.bind("<Leave>", lambda e: self.drop_frame.configure(highlightbackground="#585b70"))

        # Optionen
        opts = tk.Frame(self, bg="#1e1e2e")
        opts.pack(fill="x", padx=24, pady=10)
        
        tk.Label(opts, text="Qualität:", bg="#1e1e2e", fg="#cdd6f4",
                 font=("Segoe UI", 10)).pack(side="left")
        
        self.bitrate_var = tk.StringVar(value="192k")
        for label, val in [("128 kbps (klein)", "128k"), ("192 kbps (Standard)", "192k"),
                            ("256 kbps (gut)", "256k"), ("320 kbps (maximal)", "320k")]:
            tk.Radiobutton(
                opts, text=label, variable=self.bitrate_var, value=val,
                bg="#1e1e2e", fg="#cdd6f4", selectcolor="#313244",
                activebackground="#1e1e2e", font=("Segoe UI", 9)
            ).pack(side="left", padx=8)

        # Log-Bereich
        log_frame = tk.Frame(self, bg="#1e1e2e")
        log_frame.pack(fill="both", expand=True, padx=24, pady=(0, 8))
        
        self.log = tk.Text(
            log_frame, bg="#181825", fg="#cdd6f4", font=("Consolas", 9),
            relief="flat", bd=0, state="disabled", wrap="word",
            padx=8, pady=8
        )
        scroll = ttk.Scrollbar(log_frame, command=self.log.yview)
        self.log.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.log.pack(fill="both", expand=True)
        
        self.log.tag_configure("ok", foreground="#a6e3a1")
        self.log.tag_configure("err", foreground="#f38ba8")
        self.log.tag_configure("info", foreground="#89b4fa")

        # Statusleiste
        self.status_var = tk.StringVar(value="Bereit — Dateien auswählen oder hierher ziehen")
        tk.Label(
            self, textvariable=self.status_var, bg="#181825", fg="#a6adc8",
            font=("Segoe UI", 9), anchor="w", padx=8
        ).pack(fill="x", side="bottom")

    def _setup_dnd(self):
        """Drag & Drop via tkinterdnd2 falls verfügbar, sonst nur Klick."""
        try:
            from tkinterdnd2 import DND_FILES, TkinterDnD
            # Falls tkinterdnd2 verfügbar: drop registrieren
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind("<<Drop>>", self._on_drop)
            self.drop_label.drop_target_register(DND_FILES)
            self.drop_label.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            # Ohne DnD: nur Klick funktioniert
            pass

    def _on_drop(self, event):
        """Verarbeitet gedropte Dateien."""
        # tkinterdnd2 gibt Pfade als String zurück, manchmal mit {}
        raw = event.data
        paths = []
        # Dateipfade können Leerzeichen haben und sind dann in {} eingeschlossen
        import re
        for p in re.findall(r'\{([^}]+)\}|(\S+)', raw):
            path = p[0] or p[1]
            if path:
                paths.append(Path(path))
        self._process_paths(paths)

    def _pick_files(self):
        """Öffnet Datei-Auswahl-Dialog."""
        filetypes = [
            ("Audiodateien", " ".join(f"*{e}" for e in sorted(SUPPORTED))),
            ("Alle Dateien", "*.*"),
        ]
        paths = filedialog.askopenfilenames(title="Audiodateien auswählen", filetypes=filetypes)
        if paths:
            self._process_paths([Path(p) for p in paths])

    def _process_paths(self, paths: list[Path]):
        """Filtert und startet Konvertierung."""
        files = [p for p in paths if p.suffix.lower() in SUPPORTED and p.is_file()]
        
        if not files:
            messagebox.showwarning(
                "Keine passenden Dateien",
                f"Bitte Audiodateien wählen.\nUnterstützt: {', '.join(sorted(SUPPORTED))}"
            )
            return
        
        self._log(f"▶  {len(files)} Datei(en) werden konvertiert...\n", "info")
        self.status_var.set(f"Konvertiere {len(files)} Datei(en)...")
        
        for f in files:
            self._running += 1
            t = threading.Thread(
                target=convert_file,
                args=(f, self.bitrate_var.get(), self._log_threadsafe, self._done_threadsafe),
                daemon=True
            )
            t.start()

    def _log(self, msg: str, tag: str = ""):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _log_threadsafe(self, msg: str, tag: str = ""):
        self.after(0, lambda: self._log(msg, tag))

    def _done_threadsafe(self, success: bool):
        def _update():
            if success:
                self._success += 1
            else:
                self._failed += 1
            self._running -= 1
            if self._running == 0:
                total = self._success + self._failed
                self._log(
                    f"\n─── Fertig: {self._success} erfolgreich"
                    + (f", {self._failed} Fehler" if self._failed else "")
                    + " ───\n",
                    "info"
                )
                self.status_var.set(
                    f"Fertig — {self._success} von {total} erfolgreich konvertiert"
                )
                self._success = 0
                self._failed = 0
        self.after(0, _update)


if __name__ == "__main__":
    # Versuche tkinterdnd2 für echtes Drag & Drop
    try:
        from tkinterdnd2 import TkinterDnD
        root = TkinterDnD.Tk()
        app = App.__new__(App)
        tk.Tk.__init__(app, screenName=None, baseName=None, className="audio2mp3", useTk=True)
        App.__init__(app)
    except Exception:
        # Fallback: normales tkinter (kein Drag & Drop aber alles andere funktioniert)
        app = App()
    
    app.mainloop()
