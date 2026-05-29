import os
import subprocess
import tempfile
import shutil
import array
from logHandler import log

FFMPEG_DOWNLOAD_URL = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"

def _get_tools_dir():
    """Return the directory where ffmpeg.exe should be stored."""
    try:
        import globalVars
        base = globalVars.appArgs.configPath
    except Exception:
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "nvda")
    return os.path.join(base, "advanced_audio_themes", "ffmpeg")

def get_ffmpeg_path():
    """Return the path to ffmpeg.exe if available, else None.
    Checks: 1) config path, 2) tools dir, 3) system PATH.
    """
    from config import conf
    cfg_path = conf.get("audiothemes", {}).get("ffmpeg_path", "")
    if cfg_path and os.path.isfile(cfg_path):
        return cfg_path
    tool_exe = os.path.join(_get_tools_dir(), "ffmpeg.exe")
    if os.path.isfile(tool_exe):
        return tool_exe
    candidate = shutil.which("ffmpeg")
    if candidate:
        return candidate
    return None

def decode_with_ffmpeg(path):
    """Decode any audio file to float32 PCM using FFmpeg only.
    No processing filters applied here — TrimSilence, SmartVolume,
    SmoothEnvelope, and padding are handled in Python.
    Returns (float_array, sample_rate, channels) or None on failure.
    """
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return None
    try:
        cmd = [ffmpeg, "-y", "-i", path,
               "-f", "wav", "-acodec", "pcm_s16le",
               "-ar", "44100", "-ac", "1"]
        cmd.append("pipe:1")
        result = subprocess.run(cmd, capture_output=True, check=True, timeout=30)
        wav_data = result.stdout
        if not wav_data:
            return None
        import wave, io
        with wave.open(io.BytesIO(wav_data), "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            sample_rate = wf.getframerate()
            channels = wf.getnchannels()
            arr = array.array('h')
            arr.frombytes(frames)
            float_samples = array.array('f', [s / 32768.0 for s in arr])
            return (float_samples, sample_rate, channels)
    except subprocess.TimeoutExpired:
        log.error(f"FFmpeg decode timed out for {path}")
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg decode failed for {path}: {e.stderr.decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        log.error(f"FFmpeg decode error for {path}: {e}")
    return None

def download_ffmpeg(progress_callback=None):
    """Download and extract ffmpeg.exe with timeout and chunked progress.
    Returns path to ffmpeg.exe or None on failure.
    """
    import urllib.request
    import urllib.error
    import zipfile
    import io
    target_dir = _get_tools_dir()
    zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg-essentials.zip")
    try:
        if progress_callback:
            progress_callback(0, "Downloading FFmpeg...")
        req = urllib.request.Request(FFMPEG_DOWNLOAD_URL, method="GET")
        with urllib.request.urlopen(req, timeout=120) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 8192
            with open(zip_path, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total and progress_callback:
                        pct = int(downloaded / total * 100)
                        progress_callback(pct, f"Downloading FFmpeg... {pct}%")
        if progress_callback:
            progress_callback(50, "Extracting...")
        os.makedirs(target_dir, exist_ok=True)
        exe_path = None
        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.namelist():
                if member.endswith("ffmpeg.exe"):
                    zf.extract(member, target_dir)
                    exe_path = os.path.join(target_dir, member)
                    os.chmod(exe_path, 0o755)
                    break
        if not exe_path:
            log.error("ffmpeg.exe not found in downloaded archive")
            return None
        from config import conf
        conf["audiothemes"]["ffmpeg_path"] = exe_path
        if progress_callback:
            progress_callback(100, "FFmpeg downloaded successfully.")
        return exe_path
    except Exception as e:
        log.error(f"Failed to download FFmpeg: {e}")
        if progress_callback:
            progress_callback(-1, f"Failed: {e}")
        return None
    finally:
        try:
            os.remove(zip_path)
        except Exception:
            pass
