# Unspoken user interface feedback for NVDA
# By Bryan Smart (bryansmart@bryansmart.com) and Austin Hicks (camlorn38@gmail.com)
# Updated to use Synthizer by Mason Armstrong (mason@masonasons.me)

import os
import os.path
import time
import threading
import queue
import wave
from array import array
import struct as _struct_mod
import config
import speech
from speech.sayAll import SayAllHandler
from logHandler import log
import nvwave
from synthDriverHandler import synthChanged

# Import Steam Audio
try:
	from . import steam_audio
except ImportError as e:
	log.error(f"Failed to load Steam Audio: {e}")
	raise

sounds = dict()  # For holding instances in RAM.
sounds_lock = threading.Lock()  # Protects `sounds` from concurrent access across threads.

# Physical keyboard position map.
# Key: vkCode, or (vkCode, extended) for keys that share a vkCode.
# Value: (angle_x, angle_y) — left-to-right pan, top-to-bottom elevation.
# Positions approximate a standard 104-key QWERTY layout.
KEY_POS_MAP = \
{27: (-55, 35),
 112: (-45, 45),
 113: (-40, 45),
 114: (-35, 45),
 115: (-30, 45),
 116: (-22, 45),
 117: (-17, 45),
 118: (-12, 45),
 119: (-7, 45),
 120: (0, 45),
 121: (5, 45),
 122: (10, 45),
 123: (15, 45),
 44: (22, 35),
 145: (27, 35),
 19: (32, 35),
 192: (-55, 25),
 49: (-50, 25),
 50: (-45, 25),
 51: (-40, 25),
 52: (-35, 25),
 53: (-30, 25),
 54: (-25, 25),
 55: (-20, 25),
 56: (-15, 25),
 57: (-10, 25),
 48: (-5, 25),
 189: (0, 25),
 187: (5, 25),
 8: (12, 25),
 9: (-53, 10),
 81: (-47, 10),
 87: (-42, 10),
 69: (-37, 10),
 82: (-32, 10),
 84: (-27, 10),
 89: (-22, 10),
 85: (-17, 10),
 73: (-12, 10),
 79: (-7, 10),
 80: (-2, 10),
 219: (2, 10),
 221: (7, 10),
 220: (13, 10),
 20: (-53, -5),
 65: (-46, -5),
 83: (-41, -5),
 68: (-36, -5),
 70: (-31, -5),
 71: (-26, -5),
 72: (-21, -5),
 74: (-16, -5),
 75: (-11, -5),
 76: (-6, -5),
 186: (-1, -5),
 222: (3, -5),
 13: (11, -5),
 90: (-43, -20),
 88: (-38, -20),
 67: (-33, -20),
 86: (-28, -20),
 66: (-23, -20),
 78: (-18, -20),
 77: (-13, -20),
 188: (-8, -20),
 190: (-3, -20),
 191: (1, -20),
 160: (-51, -20),
 161: (10, -20),
 17: (-54, -35),
 91: (-48, -35),
 18: (-41, -35),
 32: (0, -35),
 162: (-4, -35),
 92: (1, -35),
 93: (8, -35),
 163: (14, -35),
 45: (22, 15),
 36: (27, 15),
 33: (32, 15),
 46: (22, -5),
 35: (27, -5),
 34: (32, -5),
 38: (27, -20),
 40: (27, -35),
 37: (22, -35),
 39: (32, -35),
 144: (40, 35),
 111: (45, 35),
 106: (50, 35),
 109: (55, 35),
 103: (40, 18),
 104: (45, 18),
 105: (50, 18),
 107: (55, 6),
 100: (40, -2),
 101: (45, -2),
 102: (50, -2),
 97: (40, -22),
 98: (45, -22),
 99: (50, -22),
 96: (42, -40),
 110: (50, -40),
 (13, 1): (55, -31)}



def pitch_shift(audio_data, pitch_factor):
	if pitch_factor == 1.0 or pitch_factor <= 0:
		return audio_data
	old_len = len(audio_data)
	new_len = int(old_len / pitch_factor)
	if new_len < 2:
		return audio_data
	
	max_idx = old_len - 1
	# Nearest neighbor interpolation for maximum performance in pure Python
	return array('f', (audio_data[int(i * pitch_factor)] if int(i * pitch_factor) <= max_idx else audio_data[max_idx] for i in range(new_len)))

def trim_silence_array(audio_data, threshold=0.01):
	"""Trim silence from the start and end of a float PCM array."""
	data_len = len(audio_data)
	if data_len == 0:
		return audio_data
	start = 0
	for i in range(data_len):
		if abs(audio_data[i]) > threshold:
			start = i
			break
	else:
		return []
	start = start & ~1  # align to even (fast bit-mask)
	end = data_len
	for i in range(data_len - 1, -1, -1):
		if abs(audio_data[i]) > threshold:
			end = i + 1
			break
	if end & 1:
		end = min(data_len, end + 1)
	return audio_data[start:end]

# taken from Stackoverflow. Don't ask.
def clamp(my_value, min_value, max_value):
	return max(min(my_value, max_value), min_value)

def floats_to_pcm_bytes(float_samples):
	"""Convert float samples to 16-bit PCM bytes. Uses fast integer math."""
	return array('h', [max(-32768, min(32767, int(s * 32767.0))) for s in float_samples]).tobytes()

def _apply_volume(float_samples, volume):
	"""Multiply all samples by volume factor. Returns new array."""
	if volume == 1.0:
		return float_samples
	return array('f', [s * volume for s in float_samples])


class UnspokenPlayer:
	def __init__(self, *args, **kwargs):
		super(UnspokenPlayer, self).__init__(*args, **kwargs)
		config.conf.spec["unspoken"] = {
			"sayAll": "boolean(default=False)",
			"speakRoles": "boolean(default=False)",
			"noSounds": "boolean(default=False)",
			"HRTF": "boolean(default=True)",
			"volumeAdjust": "boolean(default=True)",
			"Reverb": "boolean(default=False)",
			"AdaptiveReverb": "boolean(default=True)",
			"RoomSize": "integer(default=100, min=0, max=100)",
			"Damping": "integer(default=0, min=0, max=100)",
			"WetLevel": "integer(default=0, min=0, max=100)",
			"DryLevel": "integer(default=30, min=0, max=100)",
			"Width": "integer(default=100, min=0, max=100)",
			"AudioCache": "boolean(default=True)",
			"SmartVolume": "boolean(default=False)",
			"SmoothEnvelope": "boolean(default=False)",
			"SmoothPanning": "boolean(default=True)",
			"TrimSilence": "boolean(default=True)",
		}
		log.debug("Initializing Steam Audio")
		self.steam_audio = steam_audio.get_steam_audio()
		self.steam_audio_active = True
		try:
			if not self.steam_audio.initialize():
				log.warning("Steam Audio initialization returned False. Falling back to simple stereo.")
				self.steam_audio_active = False
		except Exception as e:
			log.warning(f"Failed to initialize Steam Audio: {e}. Falling back to simple stereo.")
			self.steam_audio_active = False

		# Configure reverb settings
		if self.steam_audio_active:
			self.steam_audio.set_reverb_settings(
				room_size=config.conf["unspoken"]["RoomSize"] / 100.0,
				damping=config.conf["unspoken"]["Damping"] / 100.0,
				wet_level=config.conf["unspoken"]["WetLevel"] / 100.0,
				dry_level=config.conf["unspoken"]["DryLevel"] / 100.0,
				width=config.conf["unspoken"]["Width"] / 100.0,
			)

		self.create_wave_player()
		self._last_played_object = None
		self._last_played_time = 0
		self._last_navigator_object = None

		self._audio_queue = queue.Queue()
		self._generation = 0
		self._generation_lock = threading.Lock()
		self._play_cache = {}
		self._play_cache_lock = threading.Lock()
		self._play_file_cache = {}
		self._cache_lock = threading.Lock()
		self._last_typing_time = 0.0
		self._audio_worker_thread = threading.Thread(target=self._audio_worker, daemon=True)
		self._audio_worker_thread.start()

		# these are in degrees.
		self._display_width = 180.0
		self._display_height_min = -40.0
		self._display_height_magnitude = 50.0
		synthChanged.register(self.on_synthChanged)
		self.audio3d = True
		self.use_in_say_all = True
		self.speak_roles = False
		self.use_synth_volume = True
		self.volume = 100
		self._reverb = config.conf["unspoken"]["Reverb"]
		self._room_size = config.conf["unspoken"]["RoomSize"]
		self._damping = config.conf["unspoken"]["Damping"]
		self._wet_level = config.conf["unspoken"]["WetLevel"]
		self._dry_level = config.conf["unspoken"]["DryLevel"]
		self._width = config.conf["unspoken"]["Width"]

	def _audio_worker(self):
		"""Persistent worker thread for playing audio data without spawning new threads."""
		while True:
			task = self._audio_queue.get()
			if task is None:
				self._audio_queue.task_done()
				break
				
			player, data, generation = task
			with self._generation_lock:
				if generation != self._generation:
					self._audio_queue.task_done()
					continue
			try:
				player.feed(data)
			except Exception as e:
				log.error(f"Failed to play audio in worker: {e}")
			self._audio_queue.task_done()

	@property
	def reverb(self):
		return self._reverb

	@reverb.setter
	def reverb(self, value):
		if self._reverb != value:
			self._reverb = value
			self._update_reverb_settings()

	@property
	def room_size(self):
		return self._room_size

	@room_size.setter
	def room_size(self, value):
		if self._room_size != value:
			self._room_size = value
			self._update_reverb_settings()

	@property
	def damping(self):
		return self._damping

	@damping.setter
	def damping(self, value):
		if self._damping != value:
			self._damping = value
			self._update_reverb_settings()

	@property
	def wet_level(self):
		return self._wet_level

	@wet_level.setter
	def wet_level(self, value):
		if self._wet_level != value:
			self._wet_level = value
			self._update_reverb_settings()

	@property
	def dry_level(self):
		return self._dry_level

	@dry_level.setter
	def dry_level(self, value):
		if self._dry_level != value:
			self._dry_level = value
			self._update_reverb_settings()

	@property
	def width(self):
		return self._width

	@width.setter
	def width(self, value):
		if self._width != value:
			self._width = value
			self._update_reverb_settings()

	def _update_reverb_settings(self):
		if not getattr(self, 'steam_audio_active', False):
			return
		self.steam_audio.set_reverb_settings(
			room_size=self._room_size / 100.0,
			damping=self._damping / 100.0,
			wet_level=self._wet_level / 100.0,
			dry_level=self._dry_level / 100.0,
			width=self._width / 100.0,
		)

	def create_wave_player(self):
		try:
			outputDevice = config.conf["speech"]["outputDevice"]
		except KeyError:
			outputDevice = config.conf["audio"]["outputDevice"]
		self.wave_player = nvwave.WavePlayer(
			channels=2,
			samplesPerSec=44100,
			bitsPerSample=16,
			outputDevice=outputDevice,
		)
		self.typing_players = [
			nvwave.WavePlayer(
				channels=2,
				samplesPerSec=44100,
				bitsPerSample=16,
				outputDevice=outputDevice,
			) for _ in range(5)
		]
		self._typing_player_index = 0

	def make_sound_object(self, path):
		"""Load sound files for Steam Audio processing with Caching and Normalization."""
		# LRU Cache logic
		use_cache = config.conf["unspoken"].get("AudioCache", True)
		with sounds_lock:
			if use_cache and path in sounds:
				sound = sounds.pop(path)
				sounds[path] = sound
				return sound

		# Load raw PCM data from native decoders first, then FFmpeg as fallback
		loaded = None
		ext = path.lower().split('.')[-1] if '.' in path else ''

		# Try native decoders first
		if ext == 'ogg':
			try:
				from . import ogg_vorbis
				loaded = ogg_vorbis.decode_ogg_to_float(path)
			except Exception as e:
				log.error(f"OGG decode failed for {path}: {e}")
			if loaded is None:
				result = {"path": path, "is_ogg": True}
				if use_cache:
					with sounds_lock:
						sounds[path] = result
				return result
		elif ext == 'flac':
			try:
				from . import flac_decode
				loaded = flac_decode.decode_flac_to_float(path)
			except Exception as e:
				log.error(f"FLAC decode failed for {path}: {e}")
		elif ext == 'mp3':
			try:
				from . import mp3_decode
				loaded = mp3_decode.decode_mp3_to_float(path)
			except Exception as e:
				log.error(f"MP3 decode failed for {path}: {e}")
		elif ext == 'wav':
			try:
				with wave.open(path, "rb") as wav_file:
					frames = wav_file.readframes(wav_file.getnframes())
					sample_width = wav_file.getsampwidth()
					channels = wav_file.getnchannels()
					sample_rate = wav_file.getframerate()
					if sample_width == 2:
						arr = array('h')
						arr.frombytes(frames)
						float_samples = array('f', [s / 32768.0 for s in arr])
						loaded = (float_samples, sample_rate, channels)
					elif sample_width == 1:
						float_samples = array('f', [(s - 128) / 128.0 for s in frames])
						loaded = (float_samples, sample_rate, channels)
					else:
						log.error(f"Unsupported sample width: {sample_width}")
			except Exception as e:
				log.error(f"Failed to load {path}: {e}")

		# Fall back to FFmpeg if native decode failed
		if loaded is None:
			try:
				from . import ffmpeg_utils
				loaded = ffmpeg_utils.decode_with_ffmpeg(path)
				if loaded is not None:
					ffmpeg_used = True
			except Exception as e:
				log.error(f"FFmpeg fallback decode failed for {path}: {e}")

		if loaded is None:
			log.error(f"Failed to decode audio: {path}")
			return None

		float_samples, sample_rate, channels = loaded

		# Common processing for all PCM float data
		is_mono_mode = config.conf.get("audiothemes", {}).get("output_mode", "stereo") == "mono"
		if channels == 2 and is_mono_mode:
			n = len(float_samples) // 2
			mono = array('f', [0.0]) * n
			for i in range(n):
				mono[i] = (float_samples[i * 2] + float_samples[i * 2 + 1]) * 0.5
			float_samples = mono
			channels = 1

		if config.conf["unspoken"].get("TrimSilence", False):
			float_samples = trim_silence_array(float_samples, threshold=0.01)

		if config.conf["unspoken"].get("SmartVolume", True):
			if float_samples:
				peak = max((abs(s) for s in float_samples), default=0.0)
				if peak > 0.01:
					target_peak = 0.8
					ratio = target_peak / peak
					float_samples = array('f', [s * ratio for s in float_samples])

		if config.conf["unspoken"].get("SmoothEnvelope", True):
			fade_samples = int(sample_rate * 0.01)
			num_samples = len(float_samples)
			fade_samples = min(fade_samples, num_samples // 2)
			for i in range(fade_samples):
				multiplier = i / float(fade_samples)
				float_samples[i] *= multiplier
				float_samples[num_samples - 1 - i] *= multiplier

		if config.conf["unspoken"].get("NoiseGate", False):
			from . import audio_filters
			float_samples = array('f', audio_filters.apply_noise_gate(float_samples, sample_rate=sample_rate))

		if config.conf["unspoken"].get("BassBoost", False):
			from . import audio_filters
			float_samples = array('f', audio_filters.apply_bass_boost(float_samples, sample_rate=sample_rate))

		remainder = len(float_samples) % 1024
		if remainder != 0:
			float_samples.extend(array('f', [0.0]) * (1024 - remainder))

		result = {"data": float_samples, "sample_rate": sample_rate, "path": path, "channels": channels}

		if use_cache:
			with sounds_lock:
				sounds[path] = result
				if len(sounds) > 100:
					sounds.pop(next(iter(sounds)))
		return result

	def _compute_volume(self):
		if not self.use_synth_volume:
			base_vol = self.volume / 100.0
		else:
			driver = speech.speech.getSynth()
			base_vol = getattr(driver, "volume", 100) / 100.0  # nvda reports as percent.
			base_vol = clamp(base_vol, 0.0, 1.0)
			if config.conf["unspoken"]["HRTF"]:
				base_vol += 0.25
				
		# Apply Audio Ducking if NVDA is speaking
		try:
			import time
			try:
				from .. import frenzy
				last_speech_time = frenzy.last_speech_time
			except (ImportError, AttributeError):
				last_speech_time = 0
			ducking_enabled = config.conf.get("audiothemes", {}).get("audio_ducking_enabled", True)
			if ducking_enabled and (speech.isSpeaking() or time.time() - last_speech_time < 0.5):
				duck_factor = config.conf.get("audiothemes", {}).get("audio_ducking_volume", 30) / 100.0
				base_vol *= duck_factor
		except Exception as e:
		    import logging
		    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
		return clamp(base_vol, 0.0, 1.5)

	def _play_audio_data(self, audio_bytes):
		"""Queue processed audio data for the persistent worker thread"""
		with self._generation_lock:
			gen = self._generation
		self._audio_queue.put((self.wave_player, audio_bytes, gen))

	def play(self, obj_info, sound):
		"""
		Play a sound with optional 3D positioning.
		obj_info is a plain dict with keys: name, role, location, etc.
		No COM objects are accessed here -- everything was pre-extracted.
		"""
		if not config.conf["audiothemes"]["enable_audio_themes"]:
			return
		if config.conf["unspoken"].get("noSounds", False):
			return
		if getattr(self, "use_in_say_all", False) and SayAllHandler.isRunning():
			return

		if sound.get("is_ogg"):
			import nvwave
			try:
				nvwave.playWaveFile(sound.get("path"), asynchronous=True)
			except Exception as e:
			    import logging
			    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
			return
		if "data" not in sound:
			return
		curtime = time.time()
		# De-duplicate: skip if same name played < 50ms ago, unless it's a progress bar updating
		obj_name = obj_info.get("name", "") if isinstance(obj_info, dict) else ""
		is_progress = "progress_angle" in obj_info if isinstance(obj_info, dict) else False
		if not is_progress and self._last_played_object and (curtime - self._last_played_time < 0.05 and obj_name == self._last_played_object.get("name", "")):
			return
		self._last_played_object = obj_info
		self._last_played_time = curtime
		obj_location = obj_info.get("location") if isinstance(obj_info, dict) else None
		desktop_loc = obj_info.get("desktop_location") if isinstance(obj_info, dict) else None
		force_3d = obj_info.get("force_3d", False) if isinstance(obj_info, dict) else False
		if self.audio3d or force_3d:
			# Get coordinate bounds of desktop from pre-extracted snapshot.
			# This avoids a COM call on the worker thread.
			if desktop_loc:
				desktop_max_x = desktop_loc[2]
				desktop_max_y = desktop_loc[3]
			else:
				# Fallback: assume Full HD if desktop location unavailable.
				desktop_max_x = 1920
				desktop_max_y = 1080
			# Get location of the object.
			if obj_location is not None:
				# Object has a location. Get its center.
				obj_x = obj_location[0] + (obj_location[2] / 2.0)
				obj_y = obj_location[1] + (obj_location[3] / 2.0)
			else:
				# Objects without location are assumed in the center of the screen.
				obj_x = desktop_max_x / 2.0
				obj_y = desktop_max_y / 2.0
			# Scale object position to audio display.
			angle_x = (
				(obj_x - desktop_max_x / 2.0) / desktop_max_x
			) * self._display_width
			# angle_y is a bit more involved.
			percent = (desktop_max_y - obj_y) / desktop_max_y
			angle_y = (
				self._display_height_magnitude * percent + self._display_height_min
			)
			# clamp these to Libaudioverse's internal ranges.
			angle_x = clamp(angle_x, -90.0, 90.0)
			angle_y = clamp(angle_y, -90.0, 90.0)
			
			if "progress_angle" in obj_info:
				angle_x = obj_info["progress_angle"]
				angle_y = 0.0
			
			if config.conf["unspoken"].get("SmoothPanning", True) and hasattr(self, '_last_angle_x'):
				dx = abs(angle_x - self._last_angle_x)
				dy = abs(angle_y - self._last_angle_y)
				if max(dx, dy) < 30.0:
					angle_x = (angle_x + self._last_angle_x) * 0.5
					angle_y = (angle_y + self._last_angle_y) * 0.5

			self._last_angle_x = angle_x
			self._last_angle_y = angle_y
		else:
			angle_x = 0
			angle_y = 0

		# Cache output mode once for this call
		out_mode = config.conf.get("audiothemes", {}).get("output_mode", "stereo")
		is_mono = out_mode == "mono" and not force_3d

		if is_mono:
			angle_x = 0
			angle_y = 0
			
		# Process audio with Steam Audio
		sound_data = sound
		# Adjust volume
		volume = self._compute_volume()
		
		# Pitch shifting based on progress (up to 2x pitch/speed at 100%)
		pitch_factor = 1.0
		if "progress_percent" in obj_info:
			percent = clamp(obj_info["progress_percent"], 0.0, 1.0)
			pitch_factor = 1.0 + percent

		# Cache reverb setting
		reverb_on = config.conf["unspoken"]["Reverb"]

		# Use an LRU cache for processed audio to reduce Steam Audio overhead
		cache_key = (
			sound.get("path"),
			round(angle_x, 1),
			round(angle_y, 1),
			round(volume, 2),
			reverb_on,
			round(pitch_factor, 2),
			out_mode
		)
		
		final_audio = None
		with self._play_cache_lock:
			if cache_key in self._play_cache:
				final_audio = self._play_cache.pop(cache_key)
				self._play_cache[cache_key] = final_audio

		if final_audio is None:
			audio_data = sound_data["data"]
			if pitch_factor != 1.0:
				audio_data = pitch_shift(audio_data, pitch_factor)
			adjusted_audio = _apply_volume(audio_data, volume)

			if sound_data.get("channels", 1) == 2:
				# Bypass Steam Audio to preserve original stereo separation
				final_audio = floats_to_pcm_bytes(adjusted_audio)
			elif is_mono and (not reverb_on or not self.steam_audio_active):
				# True Mono Bypass: bypass Steam Audio, duplicate mono to L/R
				import itertools
				stereo_audio = list(itertools.chain.from_iterable(zip(adjusted_audio, adjusted_audio)))
				final_audio = floats_to_pcm_bytes(stereo_audio)
			else:
				# Process with Steam Audio for 3D positioning
				processed_audio = self.steam_audio.process_sound(
					adjusted_audio, angle_x, angle_y
				)
				if not processed_audio:
					return

				# Apply reverb if enabled
				final_audio = processed_audio
				if reverb_on:
					reverb_audio = self.steam_audio.apply_reverb(processed_audio)
					if reverb_audio:
						final_audio = reverb_audio
					
			with self._play_cache_lock:
				if len(self._play_cache) > 200:
					self._play_cache.pop(next(iter(self._play_cache)))
				self._play_cache[cache_key] = final_audio

		# Play the final audio
		self.wave_player.stop()
		self._play_audio_data(final_audio)



	def play_file(self, path, volume=None, audio3d=False, ch=None, vkCode=None, angle_x=0, angle_y=0, extended=None):
		if volume is not None:
			# Typing sounds use absolute volume
			base_vol = clamp(volume / 100.0, 0.0, 1.0)
			
			# Dynamic typing velocity simulation
			import time
			now = time.monotonic()
			dt = now - self._last_typing_time
			self._last_typing_time = now
			
			# If typing fast (< 150ms per stroke), hit keys slightly harder (up to +20% volume)
			# If typing slow (> 500ms), hit keys softer (up to -10% volume)
			velocity_multiplier = 1.0
			if dt < 0.04:
				# Drop sound if typing faster than 25 strokes/sec to prevent lag
				return
			elif dt < 0.15:
				velocity_multiplier = 1.2
			elif dt < 0.3:
				velocity_multiplier = 1.05
			elif dt > 0.6:
				velocity_multiplier = 0.9
				
			final_volume = clamp(base_vol * velocity_multiplier, 0.0, 1.0)
			is_typing_sound = True
			
			# Apply Audio Ducking to typing sounds
			try:
				import time
				try:
					from .. import frenzy
					last_speech_time = frenzy.last_speech_time
				except (ImportError, AttributeError):
					last_speech_time = 0
				ducking_enabled = config.conf.get("audiothemes", {}).get("audio_ducking_enabled", True)
				if ducking_enabled and (speech.isSpeaking() or time.time() - last_speech_time < 0.5):
					duck_factor = config.conf.get("audiothemes", {}).get("audio_ducking_volume", 30) / 100.0
					final_volume *= duck_factor
			except Exception as e:
			    import logging
			    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
		else:
			final_volume = self._compute_volume()
			is_typing_sound = False

		reverb_enabled = config.conf["unspoken"]["Reverb"]
		out_mode = config.conf.get("audiothemes", {}).get("output_mode", "stereo")
		is_mono = out_mode == "mono"
		
		# For non-typing sounds, keep the caller-provided angle values (e.g. beacon).
		# For typing sounds, calculate spatial positioning below or default to center.
		if not is_typing_sound:
			pass
		else:
			angle_x = 0
			angle_y = 0
		if is_typing_sound and not is_mono:
			is_spatial = config.conf.get("audiothemes", {}).get("typing_sounds_spatial", True)
			is_smart = config.conf.get("audiothemes", {}).get("typing_sounds_spatial_smart", True)
			if is_spatial:
				if is_smart and (ch or vkCode is not None):
					if vkCode is not None:
						vk = vkCode
					else:
						import ctypes
						hwnd = ctypes.windll.user32.GetForegroundWindow()
						tid = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, 0)
						hkl = ctypes.windll.user32.GetKeyboardLayout(tid)
						vk = ctypes.windll.user32.VkKeyScanExW(ord(ch), hkl) & 0xFF
					if extended is not None:
						pos = KEY_POS_MAP.get((vk, extended))
					else:
						pos = None
					if not pos:
						pos = KEY_POS_MAP.get(vk)
					if pos:
						angle_x, angle_y = pos
				else:
					import random
					angle_x = random.uniform(-10.0, 10.0)
					
		cache_key = (path, round(final_volume, 2), audio3d, reverb_enabled, is_typing_sound, round(angle_x, 1), round(angle_y, 1), out_mode)

		final_audio = None
		with self._cache_lock:
			if cache_key in self._play_file_cache:
				final_audio = self._play_file_cache.pop(cache_key)
				self._play_file_cache[cache_key] = final_audio

		if final_audio is not None:
			if is_typing_sound:
				player = self.typing_players[self._typing_player_index]
				self._typing_player_index = (self._typing_player_index + 1) % len(self.typing_players)
				player.stop()
				self._play_typing_audio(player, final_audio)
			else:
				self.wave_player.stop()
				self._play_audio_data(final_audio)
			return

		sound = self.make_sound_object(path)
		if not sound:
			return
		if sound.get("is_ogg") and "data" not in sound:
			import nvwave
			try:
				nvwave.playWaveFile(path, asynchronous=True)
			except Exception as e:
			    import logging
			    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
			return
		
		adjusted_audio = _apply_volume(sound["data"], final_volume)

		if sound.get("channels", 1) == 2:
			if is_typing_sound and not is_mono and (angle_x != 0 or angle_y != 0):
				# Mix stereo to mono so Steam Audio can spatialize it
				n = len(adjusted_audio) // 2
				mono = [0.0] * n
				for i in range(n):
					mono[i] = (adjusted_audio[i * 2] + adjusted_audio[i * 2 + 1]) * 0.5
				adjusted_audio = mono
				processed_audio = self.steam_audio.process_sound(adjusted_audio, angle_x, angle_y)
				if not processed_audio:
					return
				final_audio = processed_audio
				if reverb_enabled:
					reverb_audio = self.steam_audio.apply_reverb(processed_audio)
					if reverb_audio:
						final_audio = reverb_audio
			else:
				# Bypass Steam Audio to preserve original stereo separation
				final_audio = floats_to_pcm_bytes(adjusted_audio)
		elif is_mono and not reverb_enabled:
			# True Mono Bypass: duplicate mono to L/R
			n = len(adjusted_audio)
			stereo_audio = [0.0] * (n * 2)
			for i in range(n):
				s = adjusted_audio[i]
				stereo_audio[i * 2] = s
				stereo_audio[i * 2 + 1] = s
			final_audio = floats_to_pcm_bytes(stereo_audio)
		else:
			processed_audio = self.steam_audio.process_sound(adjusted_audio, angle_x, angle_y)
			if not processed_audio:
				return
				
			final_audio = processed_audio
			if reverb_enabled:
				reverb_audio = self.steam_audio.apply_reverb(processed_audio)
				if reverb_audio:
					final_audio = reverb_audio

		with self._cache_lock:
			if len(self._play_file_cache) > 50:
				self._play_file_cache.pop(next(iter(self._play_file_cache)))
			self._play_file_cache[cache_key] = final_audio

		if is_typing_sound:
			player = self.typing_players[self._typing_player_index]
			self._typing_player_index = (self._typing_player_index + 1) % len(self.typing_players)
			player.stop()
			self._play_typing_audio(player, final_audio)
		else:
			self.wave_player.stop()
			self._play_audio_data(final_audio)

	def _play_typing_audio(self, player, audio_bytes):
		"""Queue typing audio data for the persistent worker thread"""
		with self._generation_lock:
			gen = self._generation
		self._audio_queue.put((player, audio_bytes, gen))

	def terminate(self):
		# Stop worker thread
		if hasattr(self, "_audio_queue"):
			self._audio_queue.put(None)
			if hasattr(self, "_audio_worker_thread"):
				self._audio_worker_thread.join(timeout=1.0)
				
		# Close WavePlayer
		if hasattr(self, "wave_player"):
			try:
				self.wave_player.close()
			except Exception as e:
			    import logging
			    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
		if hasattr(self, "typing_players"):
			for p in self.typing_players:
				try:
					p.close()
				except Exception as e:
				    import logging
				    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
		# Cleanup Steam Audio
		if hasattr(self, "steam_audio"):
			self.steam_audio.cleanup()
		synthChanged.unregister(self.on_synthChanged)

	def on_synthChanged(self, **kwargs):
		with self._generation_lock:
			self._generation += 1
		try:
			while True:
				self._audio_queue.get_nowait()
				self._audio_queue.task_done()
		except queue.Empty:
			pass
		self.wave_player.close()
		if hasattr(self, "typing_players"):
			for p in self.typing_players:
				try: p.close()
				except Exception as e:
				    import logging
				    logging.getLogger("audiothemes").error(f"AudioThemes Error: {e}", exc_info=True)
		self.create_wave_player()
