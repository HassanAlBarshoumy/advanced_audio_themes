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

def _build_filter_chain():
    """Build FFmpeg audio filter chain from config settings.
    Returns filter string or empty string.
    """
    from config import conf
    filters = []
    if conf.get("unspoken", {}).get("TrimSilence", False):
        filters.extend([
            "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB",
            "areverse",
            "silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB",
            "areverse",
        ])
    if conf.get("unspoken", {}).get("SmartVolume", True):
        filters.append("dynaudnorm=p=0.8:m=100")
    if conf.get("unspoken", {}).get("SmoothEnvelope", True):
        filters.extend([
            "afade=t=in:d=0.01",
            "afade=t=out:d=0.01",
        ])
    if filters:
        return ",".join(filters)
    return ""

def decode_with_ffmpeg(path):
    """Decode and fully process any audio file to float32 PCM using FFmpeg.
    Handles TrimSilence, SmartVolume, and SmoothEnvelope via FFmpeg filters.
    Returns (float_array, sample_rate, channels, padded_to_1024) or None on failure.
    The returned float_array is already padded to a multiple of 1024 samples.
    """
    ffmpeg = get_ffmpeg_path()
    if not ffmpeg:
        return None
    filter_str = _build_filter_chain()
    try:
        cmd = [ffmpeg, "-y", "-i", path,
               "-f", "wav", "-acodec", "pcm_s16le",
               "-ar", "44100", "-ac", "2"]
        if filter_str:
            cmd.extend(["-af", filter_str])
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
            remainder = len(float_samples) % 1024
            if remainder != 0:
                float_samples.extend(array.array('f', [0.0]) * (1024 - remainder))
            return (float_samples, sample_rate, channels)
    except subprocess.TimeoutExpired:
        log.error(f"FFmpeg decode timed out for {path}")
    except subprocess.CalledProcessError as e:
        log.error(f"FFmpeg decode failed for {path}: {e.stderr.decode('utf-8', errors='replace')[:200]}")
    except Exception as e:
        log.error(f"FFmpeg decode error for {path}: {e}")
    return None

def download_ffmpeg(progress_callback=None):
    """Download and extract ffmpeg.exe.
    Returns path to ffmpeg.exe or None on failure.
    """
    import urllib.request
    import zipfile
    target_dir = _get_tools_dir()
    zip_path = os.path.join(tempfile.gettempdir(), "ffmpeg-essentials.zip")
    try:
        if progress_callback:
            progress_callback(0, "Downloading FFmpeg...")
        urllib.request.urlretrieve(FFMPEG_DOWNLOAD_URL, zip_path)
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
