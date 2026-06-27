# Audio Themes NG & Phonetic Punctuation

This add-on provides an immersive audio experience for NVDA screen reader users by playing sounds for various UI events. It allows for the creation, installation, and customization of audio themes, enhancing the auditory feedback from the user interface.

## Features

- **Audio effects:** Plays sounds for UI events such as focusing on controls, navigating lists, and more.
- **3D Audio:** Utilizes Steam Audio to provide 3D positional audio, giving a sense of where controls are on the screen.
- **Advanced Audio DSP:** Real-time audio processing including Bass Boost, Noise Gate, Silence Trimming, Smart Volume Normalization, and Smooth Envelopes.
- **Audio Ducking:** Automatically lowers theme volume when NVDA speaks to ensure speech clarity.
- **Reverb:** Adds reverb effects to the audio for a more immersive experience.
- **Customizable Themes:** Allows users to create, install, and switch between different audio themes.
- **Audio Themes Studio V2:** A built-in tool to create new audio themes or edit existing ones directly from the microphone or via drag & drop.
- **Extended Audio Formats:** Built-in FFmpeg support for MP3, FLAC, OGG, M4A, and more.
- **Advanced Typing Sounds:** Simulates physical keyboard typing with spatial audio positioning, dynamic velocity volume adjustments, and smart key mapping for special keys (Enter, Backspace, Space, Shift, Ctrl, Alt).
- **Context-Aware Typing:** Option to restrict typing sounds to play only within editable text fields.
- **Smart Progress Bars:** Dynamic pitch shifting for progress bars (higher pitch = higher percentage).
- **First/Last Item Detection:** Plays a specific bump sound when reaching the boundary of a list or menu.
- **Audio Beacon / Sonar:** Drop a spatial audio beacon at any location on the screen and navigate around to hear real-time sonar pings guiding you relative to the beacon.
- **Advanced Navigation:** Integrated SentenceNav and BrowserNav engines for seamless text and web navigation without conflicting arrow keys.
- **Navigation Layer:** Press NVDA+Win+N to enter a fast navigation mode where arrow keys move by sentences, paragraphs, or other elements without holding modifiers.
- **Cloud Theme Store:** Download, preview, and install community-created themes directly from within the Audio Themes Studio.
- **App-Specific Profiles:** Automatically switch to a specific audio theme and typing sound pack based on the active application.

## Development & Credits

The development and consolidation of this add-on began in early May (specifically May 3, 2026) exclusively by **Hassan AlBarshoumy**.

All code refactoring, structural consolidations, and GUI integrations (including the Audio Themes Studio V2 and unified Settings dialogs) were performed to ensure maximum stability and compatibility with NVDA 2026.1+.

**Main Developer and Consolidator:**
* Hassan AlBarshoumy

**Credits & Acknowledgments:**
This add-on heavily benefited from the merging and development of previous open-source projects in the NVDA community. Special thanks to the original developers:
* **Ahmed Sami:** Original developer of the navSounds (Navigation Sound Effects) add-on and for his contributions.
* **Musharraf Omer:** Original developer of the Audio Themes 3D add-on.
* **Tony Malykh:** Original developer of the Earcons and Speech Rules, BrowserNav, SentenceNav, and TextNav add-ons.
* **Austin Hicks & Bryan Smart:** Original developers of the Unspoken add-on.

**Contact & Updates:** [https://t.me/HassanAlBarshoumy](https://t.me/HassanAlBarshoumy)

## Installation

1. Download the latest release of the add-on from Hassan's official channel.
2. Open the downloaded `.nvda-addon` file.
3. NVDA will ask you to confirm the installation. Choose "Yes".
4. Restart NVDA to complete the installation.

## How to Use

### Enabling/Disabling Audio Themes

You can enable or disable the audio themes feature in NVDA's settings:

1. Open the NVDA menu (NVDA+N).
2. Go to "Preferences" -> "Settings".
3. In the settings dialog, select the "Audio Themes" category.
4. Check or uncheck the "Enable audio themes" checkbox.

### Selecting and Managing Themes

- **About a theme:** Click the "About" button to see information about the selected theme.

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
- **Solo items behavior:** Decide if items that are the only element in a list should be treated as the first item, the last item, or ignored completely.

### Using the Audio Themes Studio V2

The Audio Themes Studio allows you to create and edit audio themes. To open the studio:

1. Open the NVDA menu (NVDA+N).
2. Select "Audio Themes Studio".

In the studio, you can:

- **Create a new audio theme:** This will guide you through the process of creating a new theme from scratch.
- **Customize an existing audio theme:** Select this option to modify the sounds of an installed theme.
- **Record from Microphone:** You can now natively record your voice or any sound directly from your microphone to be assigned to a UI event!
- **Drag & Drop:** You can drag and drop audio files directly into the Studio window to assign them rapidly.
- **Cloud Theme Store:** Browse, preview, and download community-created themes directly within the Studio, without needing external browsers.

### Exporting Your Theme

After creating or editing a theme, you can export it as an `.atp` file to share it with others. You can find the export option in the editing screen.

## Advanced Rules & Phonetic Punctuation

Earcons and Speech Rules allow NVDA to play earcons as well as other speech effects, such as prosody changes.

### Usage
1. Make sure the add-on is enabled. Press NVDA+Alt+P to toggle it.
2. Rules can be configured via a dialog box in NVDA preferences menu.
3. By default you will have a set of predefined audio rules.
4. The rules are saved in a file called `earconsAndSpeechRules.json` in your NVDA user configuration directory.

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

### 7. System Status Sounds
- **Description:** Plays audio cues for system-level events such as USB device plug/unplug, AC power changes, battery status, network connectivity, and system sleep/wake. All events are monitored through Windows native notifications (no polling).
- **Events:**
  - **AC Power Connected/Disconnected:** Plays a sound when you plug or unplug your laptop power cord.
  - **Battery Low/Critical/Full:** Plays threshold-based alerts when battery level drops below configurable percentages, or when fully charged.
  - **USB Device Plug/Unplug:** Detects any USB device connection or removal (keyboards, mice, flash drives, etc.).
  - **Storage Volume Mount/Unmount:** Detects drive letter assignment for flash drives, external hard drives, and SD cards.
  - **Network Connect/Disconnect:** Checks connectivity status at configurable intervals and plays sound on state changes.
  - **System Wake/Sleep:** Plays sounds when the computer resumes from or enters sleep mode.
- **Custom Sounds:** Place `.wav` files in your theme folder with these names:
  `sys_ac_plug.wav`, `sys_ac_unplug.wav`, `sys_battery_low.wav`, `sys_battery_critical.wav`, `sys_battery_full.wav`, `sys_usb_plug.wav`, `sys_usb_unplug.wav`, `sys_volume_plug.wav`, `sys_volume_unplug.wav`, `sys_network_connect.wav`, `sys_network_disconnect.wav`, `sys_wake.wav`, `sys_sleep.wav`
- **Configuration:** Open NVDA Settings -> Advanced Audio Themes -> "System Status" tab to enable/disable individual events, adjust volume, and set battery thresholds.

## Keyboard Shortcuts

| Key | Action |
| --- | ------ |
| **NVDA+Alt+N** | Toggle Audio Themes on/off. Press twice quickly to toggle Typing Sounds. |
| **NVDA+Alt+T** | Cycle through available Audio Themes. |
| **NVDA+Alt+Y** | Cycle through available Typing Sound packs. |
| **NVDA+Alt+K** | Toggle Typing Sounds on/off. |
| **NVDA+Alt+R** | Audio Sonar: Sweeps the active window to create an audio map of its elements. |
| **NVDA+Shift+B** | Drop/Remove an Audio Beacon at the current navigator object. |
| **NVDA+Shift+A** | Enter Audio Themes Command Layer (press this, then: h for help, t to toggle, p for rules, n/b for next/prev theme, up/down arrows for volume, y/i/u to cycle/toggle themes/typing, a/r for beacon/sonar, s for verbosity, c for heading, o for order). |
| **NVDA+Alt+P** | Toggle earcons and sound speech rules add-on. |
| **NVDA+Alt+[** | Toggle concise state reporting mode (State Verbosity). |
| **NVDA+H** | Speak current heading level. |
| **NVDA+Tab** | Report the object under the cursor with full 3D audio coordinates. |
| **NVDA+Alt+S** | Speak current sentence (SentenceNav). |
| **Alt+Arrows** | Advanced Sentence Navigation. |
| **Alt+Windows+Arrows** | Advanced Phrase Navigation. |
| **Alt+Shift+Arrows** | Advanced Paragraph Navigation. |
| **NVDA+Alt+Arrows** | Advanced Web Navigation (BrowserNav). |
| **NVDA+Win+N** | Toggle Navigation Layer (fast navigation without modifiers). |

## Translators

- **Spanish:** Hassan AlBarshoumy, Luis Carlos González Morales

## Support

For any issues, requests, or bug reports, please refer to the official contact point:
**[Hassan AlBarshoumy's Telegram](https://t.me/HassanAlBarshoumy)**
