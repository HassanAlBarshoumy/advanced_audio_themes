import os
import re

search_terms = {
    "Store/Cloud": r"(?i)(download|github|repository|store|requests\.get|urllib)",
    "App Profiles": r"(?i)(appModule|processName|profile|app_specific)",
    "Spatial Audio/Pitch": r"(?i)(spatial|hrtf|openal|elevation|distance|pitch|freq)",
    "Mouse Tracking": r"(?i)(mouseHandler|event_mouseMove|mouse_tracking)",
    "System Sounds": r"(?i)(battery|power|GetSystemPowerStatus|WLAN|network)"
}

results = {k: [] for k in search_terms}

for root, _, files in os.walk(r"c:\Users\d\AppData\Roaming\nvda\addons\advanced_audio_themes\globalPlugins\audiothemes"):
    for file in files:
        if not file.endswith(".py"): continue
        path = os.path.join(root, file)
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                for category, pattern in search_terms.items():
                    if re.search(pattern, line):
                        results[category].append(f"{file}:{i+1}")
        except:
            pass

for category, matches in results.items():
    print(f"--- {category} ---")
    if matches:
        print(f"Found {len(matches)} matches (e.g., {', '.join(matches[:5])})")
    else:
        print("No matches found.")
