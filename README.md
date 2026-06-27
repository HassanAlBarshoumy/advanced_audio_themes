# Audio Themes NG & Phonetic Punctuation

An NVDA add-on that provides an immersive audio experience through customizable sound themes, 3D positional audio, earcon rules, and advanced navigation tools.

## Features

- **Audio Themes:** Plays spatial sounds for UI events — focus changes, navigation, menus, and more.
- **3D Audio:** Steam Audio engine for positional audio that maps UI element locations.
- **Advanced Audio DSP:** Real-time audio processing including Bass Boost, Noise Gate, Silence Trimming, Smart Volume Normalization, and Smooth Envelopes.
- **Audio Ducking:** Automatically lowers theme volume when NVDA speaks to ensure speech clarity.
- **Reverb:** Realistic room simulation and acoustic effects.
- **Audio Themes Studio V2:** Built-in theme editor with microphone recording and drag-and-drop.
- **Advanced Typing Sounds:** Physical keyboard simulation with spatial positioning, dynamic velocity, and per-key mapping.
- **Context-Aware Typing:** Option to restrict typing sounds to play only within editable text fields.
- **Smart Progress Bars:** Dynamic pitch shifting for progress bars (higher pitch = higher percentage).
- **First/Last Item Detection:** Plays a specific bump sound when reaching the boundary of a list or menu.
- **Audio Beacon / Sonar:** Drop a spatial audio beacon at any location on the screen and navigate around to hear real-time sonar pings guiding you relative to the beacon.
- **Extended Audio Formats:** Built-in FFmpeg support for MP3, FLAC, OGG, M4A, and more.
- **Earcons & Speech Rules:** Custom audio cues and prosody changes for words, characters, roles, states, and formatting.
- **Phonetic Punctuation:** Hear punctuation marks as distinct sounds instead of spoken names.
- **Sentence Navigation (SentenceNav):** Alt+Arrow keys for phrase/ sentence navigation.
- **Browser Navigation (BrowserNav):** NVDA+Alt+Arrow keys for advanced web navigation.
- **Navigation Layer:** Press NVDA+Win+N to enter a fast navigation mode where arrow keys move by elements without holding modifiers.
- **Cloud Theme Store:** Download, preview, and install community-created themes directly from within the Audio Themes Studio.
- **App-Specific Profiles:** Automatically switch to a specific audio theme and typing sound pack based on the active application.

## Installation

1. Download the latest `.nvda-addon` release from the [Releases](https://github.com/HassanAlBarshoumy/advanced_audio_themes/releases) page.
2. Open the file — NVDA will prompt for confirmation.
3. Restart NVDA.

## Getting Started

### Enabling / Disabling Audio Themes

NVDA menu → Preferences → Settings → Audio Themes. Toggle "Enable audio themes".

### Switching Themes

NVDA menu → Preferences → Settings → Audio Themes, or press NVDA+Alt+T to cycle.

### Settings Tabs Overview

The Advanced Audio Themes settings panel contains several tabs to customize every aspect of the audio experience. Below is a deep dive into every available option:

#### 1. General Tab
- **Enable audio themes:** Master toggle to turn the audio themes engine on or off.
- **Select theme:** Dropdown to choose the active audio theme from installed themes.
- **About / Remove / Add New:** Manage your themes. You can install new themes from `.atp` or `.zip` files.
- **Theme Store:** Opens the built-in store to download community-created themes.
- **Theme Studio:** Opens the studio to edit or remix the currently selected theme.
- **Preview:** Plays a sequence of sample sounds from the active theme.
- **Play sounds in 3D mode:** Enables spatial audio processing.
- **Speak roles:** Toggle whether NVDA speaks control roles (like "button", "link").
- **Speak roles during say all:** Toggle role speaking during continuous reading. You can use the "Select Roles..." button to specify exactly which roles to speak.
- **Use speech synthesizer volume:** Links the theme volume to NVDA's voice volume. Disable this to use the manual slider.
- **Audio Ducking:** Lowers the volume of background audio when NVDA speaks. You can choose which categories of sound to duck and set the ducked volume percentage.
- **Fallback behaviors:** Define what happens when a sound is missing for a specific role or a first/last item (e.g., play silence, play a custom sound, or play the first available sound).
- **State sounds suppress the role sound:** If an element has a state sound (e.g., checked box), it will prevent the role sound from playing to avoid audio clutter.
- **Application Blacklist:** A comma-separated list of application executables where audio themes should be completely disabled. You can also customize which specific sound categories are suppressed in these apps.
- **Typing Sounds:** Enable typewriter or mechanical keyboard sounds. Options include spatial typing (simulating physical keyboard positions), smart spatial mapping, restricting sounds to edit boxes, selecting sound packs, and adjusting volume.
- **Configuration Management:** Check for updates, include beta releases, and Export/Import your entire configuration (including themes, rules, and sounds) to a single `.atcfg` file.

#### 2. Audio Engine Tab
- **Smart Volume Normalization:** Dynamically adjusts quiet and loud sounds to a consistent level.
- **Smooth Envelope:** Applies micro fade-ins and fade-outs to prevent audio popping or clicking.
- **Smooth 3D Panning:** Creates a glide effect when objects move across the screen rather than jumping instantly.
- **RAM Caching:** Loads sounds into memory for zero-latency playback.
- **Trim Silence:** Automatically removes silent gaps at the beginning and end of audio files based on a customizable threshold.
- **Noise Gate:** Eliminates low-level background hiss from poorly recorded audio themes. Includes Threshold, Attack, and Release sliders.
- **Bass Boost:** Enhances low frequencies to give sounds more punch. Includes Gain and Cutoff frequency sliders.
- **Audio Output Mode:** Switch between full 3D Spatial (Stereo) and Centered (Mono) audio.
- **Progress Bar Spatial Audio:** Choose whether progress bars pan from left to right based on their progress percentage, or based on their physical location on the screen. Also includes a toggle to shift the pitch higher as the progress increases.

#### 3. Reverb Tab
Simulates environmental acoustics to make sounds feel like they are played in a physical room.
- **Enable Reverb:** Master toggle for environmental effects.
- **Room Size:** Adjusts the perceived size of the virtual room.
- **Damping:** Controls how quickly high frequencies are absorbed (simulating soft vs. hard walls).
- **Wet Level / Dry Level:** Balances the amount of processed reverb vs the original clean sound.
- **Width:** Adjusts the stereo spread of the reverb tail.

#### 4. Audio Formats Tab
- **Use FFmpeg:** Enables support for compressed audio formats like MP3, FLAC, M4A, and OGG.
- **FFmpeg Status:** Shows if FFmpeg is installed. If not, a button is provided to automatically download and extract it (~12MB).

#### 5. Earcons & Speech Rules Tab
A powerful rules engine for phonetic pronunciation and custom state sounds.
- **Rules List:** Displays all active rules filtered by category (Role, State, Text, Character, etc.).
- **Rule Editor:** When adding or editing a rule, you can define:
  - **Pattern / Frenzy Value:** The regex pattern, role, or state to match.
  - **Action Type:** Choose to play a built-in wave, a custom wav file, a beep, adjust prosody (pitch/rate), replace text, or do nothing.
  - **Speech Action:** Decide whether NVDA should keep the original text, edit the spoken text, or be completely silenced when the rule matches.
  - **Audio Adjustments:** Volume slider, start/end trim offsets (in milliseconds), tone/duration for beeps.
  - **Filters:** Restrict the rule to specific applications, window titles, or website URLs (Regex supported).
- **Batch Operations:** Export/Import rule dictionaries, enable/disable all rules, or test rules directly from the interface.

#### 6. Miscellaneous Tab
Advanced configuration for navigation modules.
- **Sentence Navigation (Alt+Arrows):** Adjust chime volumes for paragraph boundaries, toggle formatting announcements, configure Wikipedia reference skipping, adjust sentence reconstruction across paragraphs, and define custom sentence/phrase breaking punctuation characters.
- **Text Navigation (Alt+Shift+Arrows):** Adjust crackle volume and configure end-of-text chime behaviors.
- **Advanced Browser Navigation (BrowserNav):** Adjust crackling and beeping volumes during QuickSearch navigation, and skip clutter chime volume.
- **Navigation Layer (NVDA+Windows+N):** Configure auto-exit timeouts, layer action sounds, pass-through keys, and toggle specific navigation modes on or off.

#### 7. Speech Order Tab
- **Global announcement format:** Change how NVDA reads elements globally (e.g., Default: Name -> Role -> State, or State -> Role -> Name).
- **Per-role customization:** Use the search box to find specific roles (like Checkbox or Link) and assign a unique announcement format just for them.

#### 8. App Profiles Tab
- Automatically switch audio experiences based on the active application.
- **Add Profile:** Enter an application executable (e.g., `chrome.exe` or `devenv.exe`) and assign a specific Audio Theme and/or Typing Sound Pack that will activate instantly when you switch to that app.

#### 9. QuickSearch & Bookmarks Tab
- Manage domain-specific navigation rules for web browsing.
- Assign keystrokes (like J or K) to quickly jump to specific elements (QuickJump), automatically skip cluttered menus (SkipClutter), or execute custom Python scripts (Script bookmarks) on specific websites.

#### 10. First/Last Item Tab
- **Enable first/last item detection:** Plays a unique bump sound when you reach the top or bottom of a list, menu, or treeview.
- **Detection scope:** Apply this universally to all roles, or selectively to specific roles (using the Select Roles button).
### Opening the Studio

NVDA menu → Audio Themes Studio (or NVDA+Shift+A then 's').

### State Verbosity
The add-on includes a feature that allows you to mute and hide the speech or sounds for states that might cause constant annoyance (e.g., the "expanded" or "not selected" states).
To utilize this feature:
1. Go to the Speech Rules settings and edit the state you wish to mute.
2. Check the option labeled **"Suppress state clutter"**.
3. Now you can use the quick shortcut to toggle the verbosity level whenever you want.
* You can toggle this option either via the layer shortcut **(NVDA+Shift+A then s)** or via the direct shortcut **(NVDA+Alt+[)**.
* When you reduce the verbosity, any state for which you have enabled this option will be muted. When you increase the verbosity back, the add-on will return to reading all states normally.

## Advanced Features & Secrets

A set of highly advanced features are integrated into this add-on which might not be obvious at first glance:

### 1. Navigation Layer
- **Shortcut:** `NVDA+Win+N`
- **Description:** Once you enter this layer, you no longer need to hold `Alt`, `Shift`, or any modifier key to navigate. You can use just the arrow keys!
- **How to use:**
  - Use Left/Right Arrows to cycle through **27 different navigation modes** (Character, Word, Line, Sentence, Paragraph, Heading, Link, Button, Edit field, Table, etc.).
  - Use Up/Down Arrows to jump to the previous/next item based on the current mode.
  - Press `C` to copy the current item to the clipboard.
  - Press `S` to spell the current item.
  - Press `R` to Read All starting from the current item.
  - Press `Escape` to exit the layer.

### 2. Audio Sonar
- **Shortcut:** `NVDA+Alt+R` (or `NVDA+Shift+A` then `r`)
- **Description:** An incredible feature that sweeps the entire active window, collects all controls inside it (buttons, lists, texts), and rapidly plays their associated sounds from left to right in 3D space. This gives you a sonic "picture" of the window's layout and how populated it is!

### 3. Audio Beacon
- **Shortcut:** `NVDA+Shift+B` (or `NVDA+Shift+A` then `a`)
- **Description:** You can "drop" an audio beacon at the current navigator object's location. This is useful to mark an object and track it contextually during an Audio Sonar sweep.

### 4. Audio Themes Command Layer
- **Shortcut:** `NVDA+Shift+A`
- **Description:** Instead of memorizing dozens of shortcuts, enter this layer and press a single key to execute a command:
  - `t` : Toggle Audio Themes on/off.
  - `p` : Toggle Earcons & Speech Rules.
  - `n` and `b` : Next/Previous Theme.
  - `Up Arrow` and `Down Arrow` : Increase/Decrease theme volume.
  - `s` : Toggle State Verbosity.
  - `o` : Rapidly cycle Speech Order (e.g. Name then Role, or Role then Name).
  - `c` : Speak current heading level.
  - `y` : Cycle through themes.
  - `i` : Cycle through typing sounds.
  - `u` : Toggle typing sounds.
  - `h` : Help.

### 5. 3D Object Reporting
- **Shortcut:** `NVDA+Tab`
- **Description:** Reports the current object under the cursor, but perfectly maps its 3D spatial audio coordinates so you can hear its exact physical location on your screen relative to the center.

### 6. System Tray Integration
- **Description:** The add-on injects quick-access options directly into NVDA's System Tray menu. You can right-click the NVDA icon next to the clock on your taskbar to instantly access the "Audio Themes Studio" or toggle the themes on/off without needing to open the full preferences dialog.

## Keyboard Shortcuts

| Key | Action |
| --- | ------ |
| NVDA+Alt+N | Toggle Audio Themes (press twice for Typing Sounds) |
| NVDA+Alt+T | Cycle audio themes |
| NVDA+Alt+Y | Cycle typing sound packs |
| NVDA+Alt+K | Toggle typing sounds |
| NVDA+Alt+R | Audio Sonar: sweep active window for an audio map |
| NVDA+Shift+B | Drop / remove audio beacon |
| NVDA+Shift+A | Audio Themes command layer (h=help, t=toggle, p=rules, n/b=next/prev theme, arrows=volume, y/i/u=cycle/toggle, a/r=beacon/sonar, s=verbosity, c=heading, o=order) |
| NVDA+Alt+P | Toggle earcons and speech rules |
| NVDA+Alt+[ | Toggle concise state reporting |
| NVDA+H | Speak current heading level |
| NVDA+Tab | Report object with 3D coordinates |
| NVDA+Alt+S | Speak current sentence (SentenceNav) |
| Alt+Arrows | Sentence navigation |
| Alt+Windows+Arrows | Phrase navigation |
| Alt+Shift+Arrows | Paragraph navigation |
| NVDA+Alt+Arrows | Web browser navigation |
| NVDA+Win+N | Toggle Navigation Layer (fast navigation without modifiers) |

## Credits

The development and consolidation of this add-on began in early May (specifically May 3, 2026) exclusively by **Hassan AlBarshoumy**.

All code refactoring, structural consolidations, and GUI integrations (including the Audio Themes Studio V2 and unified Settings dialogs) were performed to ensure maximum stability and compatibility with NVDA 2026.1+.

**Main Developer and Consolidator:**
* Hassan AlBarshoumy

**Acknowledgments:**
This add-on heavily benefited from the merging and development of previous open-source projects in the NVDA community. Special thanks to the original developers:
* **Ahmed Sami:** Original developer of the navSounds (Navigation Sound Effects) add-on and for his contributions.
* **Musharraf Omer:** Original developer of the Audio Themes 3D add-on.
* **Tony Malykh:** Original developer of the Earcons and Speech Rules, BrowserNav, SentenceNav, and TextNav add-ons.
* **Austin Hicks & Bryan Smart:** Original developers of the Unspoken add-on.

## Links

- **Telegram:** [t.me/HassanAlBarshoumy](https://t.me/HassanAlBarshoumy)
- **GitHub:** [github.com/HassanAlBarshoumy/advanced_audio_themes](https://github.com/HassanAlBarshoumy/advanced_audio_themes)

## License

Refer to the add-on's license file for details.
