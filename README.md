# audio2mp3

Portabler Audio-Konverter — wandelt m4a, aac, wav, flac, ogg, opus, wma in MP3 um.

**Kein Admin nötig.** ffmpeg wird beim ersten Start automatisch in `~/.audio2mp3/` heruntergeladen.

## Voraussetzungen

- Python 3.8+ (ohne Admin installierbar via [python.org](https://www.python.org/downloads/) → "Add to PATH" aktivieren)
- Keine weiteren Pakete nötig — nur die Python-Standardbibliothek

## Installation

```bash
# Repository klonen (oder ZIP herunterladen)
git clone https://github.com/tobboehnke/audio2mp3.git
cd audio2mp3
```

Fertig. Beim ersten Start wird ffmpeg automatisch heruntergeladen.

## Nutzung

```bash
# Eine Datei konvertieren
python audio2mp3.py aufnahme.m4a

# Mehrere Dateien
python audio2mp3.py datei1.m4a datei2.wav datei3.aac

# Ganzen Ordner konvertieren (inkl. Unterordner)
python audio2mp3.py ~/Downloads/musik/

# Höhere Qualität (320 kbps)
python audio2mp3.py podcast.m4a --bitrate 320k

# In anderen Ordner konvertieren
python audio2mp3.py aufnahme.m4a --output ~/Podcasts/

# Vorhandene Dateien überschreiben
python audio2mp3.py *.m4a --overwrite
```

## Unterstützte Formate

| Format | Beschreibung |
|--------|-------------|
| `.m4a` | Apple Audio (iTunes, iPhone-Aufnahmen) |
| `.aac` | Advanced Audio Coding |
| `.wav` | Unkomprimiertes Audio |
| `.flac` | Verlustfreies Audio |
| `.ogg` | Ogg Vorbis |
| `.opus` | Opus Audio (Telegram, WhatsApp) |
| `.wma` | Windows Media Audio |
| `.mp4` | Video → nur Audio extrahieren |
| `.webm` | WebM → nur Audio extrahieren |

## Optionen

| Option | Standard | Beschreibung |
|--------|----------|-------------|
| `--bitrate` / `-b` | `192k` | MP3-Bitrate: 128k, 192k, 256k, 320k |
| `--output` / `-o` | Gleicher Ordner | Ausgabeordner |
| `--overwrite` | Nein | Vorhandene MP3s überschreiben |
| `--ffmpeg` | Auto | Eigenen ffmpeg-Pfad angeben |

## Wo landet ffmpeg?

Beim ersten Start wird ffmpeg heruntergeladen nach:
- **Windows:** `C:\Users\<Name>\.audio2mp3\ffmpeg\ffmpeg.exe`
- **macOS/Linux:** `~/.audio2mp3/ffmpeg/ffmpeg`

Das passiert nur einmal. Danach wird die lokale Kopie verwendet.

Falls ffmpeg bereits im System-PATH vorhanden ist, wird es direkt genutzt (kein Download).

## Tipps

**iPhone-Sprachmemos (m4a) konvertieren:**
```bash
python audio2mp3.py ~/Downloads/Sprachmemo.m4a --bitrate 128k
```

**Alle m4a-Dateien im Downloads-Ordner auf einmal:**
```bash
python audio2mp3.py ~/Downloads/ --output ~/Musik/mp3/
```

**Podcast-Archiv mit maximaler Qualität:**
```bash
python audio2mp3.py ~/Podcasts/ --bitrate 320k --overwrite
```
