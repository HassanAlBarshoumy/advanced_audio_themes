def get_x(u): return int((u - 11.5) * 5.0)

KEY_POS_MAP_GEN = {
	# Row 0: Escape, Function keys, Print Screen / Scroll Lock / Pause (+35° elevation)
	0x1B: (get_x(0.5), 35),	# Escape
	0x70: (get_x(2.5), 45),	# F1
	0x71: (get_x(3.5), 45),	# F2
	0x72: (get_x(4.5), 45),	# F3
	0x73: (get_x(5.5), 45),	# F4
	0x74: (get_x(7.0), 45),	# F5
	0x75: (get_x(8.0), 45),	# F6
	0x76: (get_x(9.0), 45),	# F7
	0x77: (get_x(10.0), 45),	# F8
	0x78: (get_x(11.5), 45),	# F9
	0x79: (get_x(12.5), 45),	# F10
	0x7A: (get_x(13.5), 45),	# F11
	0x7B: (get_x(14.5), 45),	# F12
	0x2C: (get_x(16.0), 35),	# Print Screen
	0x91: (get_x(17.0), 35),	# Scroll Lock
	0x13: (get_x(18.0), 35),	# Pause / Break

	# Row 1: Number row (+25° elevation)
	0xC0: (get_x(0.5), 25),	# `
	0x31: (get_x(1.5), 25),	# 1
	0x32: (get_x(2.5), 25),	# 2
	0x33: (get_x(3.5), 25),	# 3
	0x34: (get_x(4.5), 25),	# 4
	0x35: (get_x(5.5), 25),	# 5
	0x36: (get_x(6.5), 25),	# 6
	0x37: (get_x(7.5), 25),	# 7
	0x38: (get_x(8.5), 25),	# 8
	0x39: (get_x(9.5), 25),	# 9
	0x30: (get_x(10.5), 25),	# 0
	0xBD: (get_x(11.5), 25),	# -
	0xBB: (get_x(12.5), 25),	# =
	0x08: (get_x(14.0), 25),	# Backspace

	# Row 2: QWERTY row (+10° elevation)
	0x09: (get_x(0.75), 10),	# Tab
	0x51: (get_x(2.0), 10),	# Q
	0x57: (get_x(3.0), 10),	# W
	0x45: (get_x(4.0), 10),	# E
	0x52: (get_x(5.0), 10),	# R
	0x54: (get_x(6.0), 10),	# T
	0x59: (get_x(7.0), 10),	# Y
	0x55: (get_x(8.0), 10),	# U
	0x49: (get_x(9.0), 10),	# I
	0x4F: (get_x(10.0), 10),	# O
	0x50: (get_x(11.0), 10),	# P
	0xDB: (get_x(12.0), 10),	# [
	0xDD: (get_x(13.0), 10),	# ]
	0xDC: (get_x(14.25), 10),	# \

	# Row 3: ASDF homerow (-5° elevation)
	0x14: (get_x(0.875), -5),	# Caps Lock
	0x41: (get_x(2.25), -5),	# A
	0x53: (get_x(3.25), -5),	# S
	0x44: (get_x(4.25), -5),	# D
	0x46: (get_x(5.25), -5),	# F
	0x47: (get_x(6.25), -5),	# G
	0x48: (get_x(7.25), -5),	# H
	0x4A: (get_x(8.25), -5),	# J
	0x4B: (get_x(9.25), -5),	# K
	0x4C: (get_x(10.25), -5),	# L
	0xBA: (get_x(11.25), -5),	# ;
	0xDE: (get_x(12.25), -5),	# '
	0x0D: (get_x(13.875), -5),	# Enter

	# Row 4: ZXCV row (-20° elevation)
	0x5A: (get_x(2.75), -20),	# Z
	0x58: (get_x(3.75), -20),	# X
	0x43: (get_x(4.75), -20),	# C
	0x56: (get_x(5.75), -20),	# V
	0x42: (get_x(6.75), -20),	# B
	0x4E: (get_x(7.75), -20),	# N
	0x4D: (get_x(8.75), -20),	# M
	0xBC: (get_x(9.75), -20),	# ,
	0xBE: (get_x(10.75), -20),	# .
	0xBF: (get_x(11.75), -20),	# /
	0xA0: (get_x(1.125), -20),	# L-Shift
	0xA1: (get_x(13.625), -20),	# R-Shift

	# Row 5: Bottom row (Space bar row, -35° elevation)
	0x11: (get_x(0.625), -35),	# L-Ctrl
	0x5B: (get_x(1.875), -35),	# L-Win
	0x12: (get_x(3.125), -35),	# L-Alt
	0x20: (get_x(6.875), -35),	# Space
	0xA2: (get_x(10.625), -35),	# R-Alt / AltGr
	0x5C: (get_x(11.875), -35),	# R-Win
	0x5D: (get_x(13.125), -35),	# Menu / Apps
	0xA3: (get_x(14.375), -35),	# R-Ctrl

	# Navigation cluster
	0x2D: (get_x(16.0), 15),		# Insert
	0x24: (get_x(17.0), 15),		# Home
	0x21: (get_x(18.0), 15),		# Page Up
	0x2E: (get_x(16.0), -5),		# Delete
	0x23: (get_x(17.0), -5),		# End
	0x22: (get_x(18.0), -5),		# Page Down
	0x26: (get_x(17.0), -20),	# Up
	0x28: (get_x(17.0), -35),	# Down
	0x25: (get_x(16.0), -35),	# Left
	0x27: (get_x(18.0), -35),	# Right

	# Numpad
	0x90: (get_x(19.5), 35),		# Num Lock
	0x6F: (get_x(20.5), 35),		# Numpad /
	0x6A: (get_x(21.5), 35),		# Numpad *
	0x6D: (get_x(22.5), 35),	# Numpad -
	0x67: (get_x(19.5), 18),		# Numpad 7
	0x68: (get_x(20.5), 18),		# Numpad 8
	0x69: (get_x(21.5), 18),		# Numpad 9
	0x6B: (get_x(22.5), 6),	    # Numpad +
	0x64: (get_x(19.5), -2),		# Numpad 4
	0x65: (get_x(20.5), -2),		# Numpad 5
	0x66: (get_x(21.5), -2),		# Numpad 6
	0x61: (get_x(19.5), -22),	# Numpad 1
	0x62: (get_x(20.5), -22),	# Numpad 2
	0x63: (get_x(21.5), -22),	# Numpad 3
	0x60: (get_x(20.0), -40),	# Numpad 0
	0x6E: (get_x(21.5), -40),	# Numpad .
	(0x0D, 1): (get_x(22.5), -31),	# Numpad Enter (midpoint of row 4 and 5)
}

import pprint
with open("C:/Users/d/AppData/Roaming/nvda/addons/advanced_audio_themes/globalPlugins/audiothemes/unspoken/new_map.py", "w") as f:
    f.write("KEY_POS_MAP = \\\n")
    f.write(pprint.pformat(KEY_POS_MAP_GEN, sort_dicts=False))
    f.write("\n")
