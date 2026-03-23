#!/usr/bin/env python3
"""
audio2mp3 — Portable Audio Converter
Konvertiert m4a, aac, wav, flac, ogg, opus, wma → mp3

Kein Admin nötig: ffmpeg wird beim ersten Start automatisch
in ~/.audio2mp3/ heruntergeladen.

Nutzung:
  python audio2mp3.py datei.m4a
  python audio2mp3.py ordner/
  python audio2mp3.py datei1.m4a datei2.wav --bitrate 192k
  python audio2mp3.py datei.m4a --output /zielordner/
"""

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.request
import zipfile
import tarfile
from pathlib import Path

# ── Konfiguration ──────────────────────────────────────────────────────────────

SUPPORTED_FORMATS = {".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".wma", ".mp4", ".webm"}
FFMPEG_DIR = Path.home() / ".audio2mp3" / "ffmpeg"

# Portable ffmpeg Downloads (statisch gelinkt, kein Install nötig)
FFMPEG_URLS = {
    "Windows": {
        "url": "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "binary": "ffmpeg.exe",
        "strip_components": 2,  # zip enthält ffmpeg-xxx/bin/ffmpeg.exe
    },
    "Darwin": {
        "url": "https://evermeet.cx/ffmpeg/getrelease/ffmpeg/zip",
        "binary": "ffmpeg",
        "strip_components": 0,
    },
    "Linux": {
        "url": "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
        "binary": "ffmpeg",
        "strip_components": 1,
    },
}


# ── ffmpeg Bootstrap ───────────────────────────────────────────────────────────

def find_ffmpeg() -> str | None:
    """Sucht ffmpeg: zuerst lokal in ~/.audio2mp3/, dann im PATH."""
    system = platform.system()
    binary = "ffmpeg.exe" if system == "Windows" else "ffmpeg"

    # Lokales ffmpeg (einmalig heruntergeladen)
    local = FFMPEG_DIR / binary
    if local.exists():
        return str(local)

    # System-ffmpeg
    found = shutil.which("ffmpeg")
    if found:
        return found

    return None


def download_ffmpeg() -> str:
    """Lädt portables ffmpeg herunter — kein Admin nötig."""
    system = platform.system()
    if system not in FFMPEG_URLS:
        raise RuntimeError(f"Unbekanntes Betriebssystem: {system}")

    cfg = FFMPEG_URLS[system]
    FFMPEG_DIR.mkdir(parents=True, exist_ok=True)
    binary_name = cfg["binary"]
    dest = FFMPEG_DIR / binary_name

    print(f"⬇  Lade portables ffmpeg herunter ({system})...")
    print(f"   Quelle: {cfg['url']}")
    print(f"   Ziel:   {FFMPEG_DIR}")
    print("   (Einmalig, danach wird es lokal gecacht)\n")

    archive = FFMPEG_DIR / "ffmpeg_download.tmp"

    def progress(count, block_size, total):
        if total > 0:
            pct = min(100, int(count * block_size * 100 / total))
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            print(f"\r   [{bar}] {pct}%", end="", flush=True)

    urllib.request.urlretrieve(cfg["url"], archive, reporthook=progress)
    print()

    # Entpacken
    print("📦 Entpacke...")
    if archive.suffix == ".zip" or str(archive).endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            # ffmpeg.exe / ffmpeg aus dem zip holen
            for member in z.namelist():
                if member.endswith(binary_name) and not member.endswith("/"):
                    z.extract(member, FFMPEG_DIR)
                    extracted = FFMPEG_DIR / member
                    extracted.rename(dest)
                    break
    else:
        # tar.xz / tar.gz
        with tarfile.open(archive) as t:
            for member in t.getmembers():
                if member.name.endswith(binary_name) and member.isfile():
                    member.name = binary_name
                    t.extract(member, FFMPEG_DIR)
                    break

    archive.unlink(missing_ok=True)

    # Ausführbar machen (Unix)
    if system != "Windows":
        dest.chmod(dest.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    print(f"✅ ffmpeg installiert: {dest}\n")
    return str(dest)


def get_ffmpeg() -> str:
    """Gibt Pfad zu ffmpeg zurück, lädt es bei Bedarf herunter."""
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        return ffmpeg
    return download_ffmpeg()


# ── Konvertierung ──────────────────────────────────────────────────────────────

def convert_file(
    input_path: Path,
    output_path: Path,
    ffmpeg: str,
    bitrate: str = "192k",
    overwrite: bool = False,
) -> bool:
    """Konvertiert eine Audiodatei zu MP3. Gibt True bei Erfolg zurück."""
    if output_path.exists() and not overwrite:
        print(f"  ⏭  Übersprungen (existiert bereits): {output_path.name}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-i", str(input_path),
        "-vn",               # kein Video
        "-ar", "44100",      # Sample Rate
        "-ac", "2",          # Stereo
        "-b:a", bitrate,     # Bitrate
        "-f", "mp3",
        "-y" if overwrite else "-n",
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"  ✅ {input_path.name} → {output_path.name} ({size_mb:.1f} MB)")
        return True
    else:
        # ffmpeg gibt Fehler auf stderr aus
        error_lines = [l for l in result.stderr.split("\n") if "Error" in l or "Invalid" in l or "No such" in l]
        error_msg = error_lines[-1] if error_lines else result.stderr.split("\n")[-3]
        print(f"  ❌ {input_path.name}: {error_msg.strip()}")
        return False


def collect_files(paths: list[Path]) -> list[Path]:
    """Sammelt alle konvertierbaren Dateien aus Pfaden (auch Ordner rekursiv)."""
    files = []
    for path in paths:
        if path.is_dir():
            for ext in SUPPORTED_FORMATS:
                files.extend(path.rglob(f"*{ext}"))
                files.extend(path.rglob(f"*{ext.upper()}"))
        elif path.is_file():
            if path.suffix.lower() in SUPPORTED_FORMATS:
                files.append(path)
            else:
                print(f"⚠  Unbekanntes Format: {path.suffix} — {path.name}")
    return sorted(set(files))


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="audio2mp3 — Konvertiert Audiodateien zu MP3 (kein Admin nötig)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python audio2mp3.py aufnahme.m4a
  python audio2mp3.py ~/Downloads/musik/          # ganzen Ordner konvertieren
  python audio2mp3.py *.m4a --bitrate 320k
  python audio2mp3.py podcast.m4a --output ~/Podcasts/
  python audio2mp3.py datei.m4a --overwrite

Unterstützte Formate: m4a, aac, wav, flac, ogg, opus, wma, mp4, webm
        """,
    )
    parser.add_argument("inputs", nargs="+", help="Dateien oder Ordner")
    parser.add_argument(
        "--bitrate", "-b",
        default="192k",
        help="MP3-Bitrate (z.B. 128k, 192k, 256k, 320k) — Standard: 192k",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Ausgabeordner (Standard: gleicher Ordner wie Quelldatei)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Vorhandene MP3-Dateien überschreiben",
    )
    parser.add_argument(
        "--ffmpeg",
        default=None,
        help="Pfad zu ffmpeg (optional, wird sonst automatisch gefunden/geladen)",
    )

    args = parser.parse_args()

    # ffmpeg besorgen
    ffmpeg = args.ffmpeg or get_ffmpeg()
    version = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True)
    ver_line = version.stdout.split("\n")[0] if version.returncode == 0 else "?"
    print(f"🎵 audio2mp3  |  {ver_line}\n")

    # Dateien sammeln
    input_paths = [Path(p) for p in args.inputs]
    files = collect_files(input_paths)

    if not files:
        print("❌ Keine unterstützten Audiodateien gefunden.")
        print(f"   Unterstützt: {', '.join(sorted(SUPPORTED_FORMATS))}")
        sys.exit(1)

    print(f"📂 {len(files)} Datei(en) gefunden — Bitrate: {args.bitrate}\n")

    # Ausgabeordner
    output_dir = Path(args.output) if args.output else None
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    # Konvertieren
    success = 0
    failed = 0

    for f in files:
        dest_dir = output_dir or f.parent
        dest = dest_dir / (f.stem + ".mp3")
        ok = convert_file(f, dest, ffmpeg, bitrate=args.bitrate, overwrite=args.overwrite)
        if ok:
            success += 1
        else:
            failed += 1

    # Zusammenfassung
    print(f"\n{'─' * 40}")
    print(f"✅ Erfolgreich: {success}   ❌ Fehler: {failed}")
    if output_dir:
        print(f"📁 Ausgabe in: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
