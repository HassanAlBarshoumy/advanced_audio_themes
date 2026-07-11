# Advanced Audio Themes

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
- **System Status Sounds:** Plays audio cues for system-level events such as AC power changes, battery status, USB device connection, and network connectivity.
- **Emoji Enhancement:** Full emoji detection engine with CLDR-based categorization (9 categories), customizable sounds per category, speech prefix/suffix insertion, and per-emoji or per-block repeat modes.
- **Clipboard Announcements:** Audio and speech feedback for clipboard operations (Copy, Cut, Paste, Select All, Undo, Redo, Paste Plain Text) with per-action customization and configurable delay.

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

#### 11. System Status Tab
- **Enable system status sounds:** Master toggle for all hardware/system event audio cues.
- **USB Monitoring:** Toggle monitoring of USB connections (keyboards, flash drives, etc.) and storage mount events.
- **Events:** Individual toggles to enable or disable specific event notifications like Battery charging/discharging, Power state changes, and Network connectivity changes.

#### 12. Clipboard Tab
- **Enable clipboard announcements:** Master toggle for audio and speech feedback on clipboard actions.
- **Announcement Mode:** Choose between "Speech and Sound", "Speech only", or "Sound only".
- **Sound volume:** Adjust the volume of clipboard action sounds.
- **Announcement delay (ms):** Fine-tune the delay before the announcement plays (0-500ms).
- **Per-Action Settings:** A detailed list of all clipboard actions (Copy, Cut, Paste, Select All, Undo, Redo, Paste Plain Text, Alternate Redo) where you can individually enable/disable each action, toggle its sound, toggle its speech, and set custom announcement text.

#### 13. Emoji Tab
- **Enable emoji sounds and speech prefix:** Master toggle for the entire emoji enhancement system.
- **Sound Settings:**
  - **Play sound when emoji is encountered:** Toggle emoji sounds.
  - **Sound position:** Choose when the sound plays: Before emoji, After emoji, Before and after, or No sound.
  - **Sound repeat:** Play the sound once per individual emoji character, or once per text block.
  - **Volume:** Adjust emoji sound volume (0-100%).
  - **Delay before/after sound (ms):** Fine-tune timing of emoji sounds.
- **Speech Prefix Settings:**
  - **Speak prefix text before emoji descriptions:** Toggle the spoken prefix.
  - **Prefix text:** The word spoken before the emoji description (default: "emoji").
  - **Suffix text:** The word spoken after the emoji description.
  - **Prefix position:** Choose where the prefix appears: Before, After, Both, or None.
  - **Prefix repeat:** Speak once per emoji character, or once per text block.
- **Category-based sounds:** Each of the 9 CLDR emoji categories (Smileys, People, Animals, Food, Travel, Activities, Objects, Symbols, Flags) has its own toggle and can have a unique sound file in your theme folder.
- **Suppress role sound when emoji is present:** Prevents the UI role sound from playing when the focused element contains emojis.
- **Emoji blacklist:** Exclude specific emojis from triggering sounds.
- **Custom descriptions:** Override the default emoji description with your own text (JSON format).

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
- **Description:** A highly optimized, isolated navigation environment designed to accelerate text and web browsing. Once entered, you are freed from holding modifier keys like `Alt` or `Shift`. You can navigate effortlessly using just the arrow keys, reducing finger strain and speeding up your workflow.

#### Layer Controls
| Key | Action |
| --- | ------ |
| **Left Arrow** | Previous navigation mode |
| **Right Arrow** | Next navigation mode |
| **Up Arrow** | Move to previous item in current mode |
| **Down Arrow** | Move to next item in current mode |
| **C** | Copy the text of the current unit to the clipboard |
| **S** | Spell out the text of the current unit letter by letter |
| **Escape** | Exit the navigation layer and return to normal operation |

#### All 27 Navigation Modes
The 27 modes are split into two groups: **text modes** (navigate by reading units) and **web element modes** (jump to specific HTML elements). You cycle through all enabled modes using Left/Right arrows.

**Text Modes (arrow-key driven):**
1. **Character** — Navigate one character at a time (left/right arrows)
2. **Word** — Navigate one word at a time
3. **Line** — Navigate one line at a time
4. **Sentence** — Navigate one sentence at a time
5. **Paragraph** — Navigate one paragraph at a time

**Web Element Modes (single-key driven via NVDA's quicknav):**
6. **Heading** (`H`) — Jump between headings of all levels
7. **Link** (`K`) — Jump between links
8. **Unvisited Link** (`U`) — Jump between unvisited links only
9. **Visited Link** (`V`) — Jump between visited links only
10. **Form Field** (`F`) — Jump between form fields (input, select, textarea)
11. **Button** (`B`) — Jump between buttons
12. **Edit Field** (`E`) — Jump between editable text fields
13. **Check Box** (`X`) — Jump between check boxes
14. **Combo Box** (`C`) — Jump between combo boxes / drop-down lists
15. **Radio Button** (`R`) — Jump between radio buttons
16. **Image** (`G`) — Jump between images and graphics
17. **List** (`L`) — Jump between HTML lists
18. **List Item** (`I`) — Jump between individual list items
19. **Table** (`T`) — Jump between HTML tables
20. **Frame** (`M`) — Jump between frames and iframes
21. **Article** (`A`) — Jump between article elements
22. **Landmark** (`D`) — Jump between ARIA landmark regions
23. **Separator** (`S`) — Jump between separators / horizontal rules
24. **Quote** (`Q`) — Jump between block quotes
25. **Object** (`O`) — Jump between embedded objects (Flash, Java, etc.)
26. **Text Block** (`N`) — Jump between text blocks
27. **Search** (`F3`) — Jump between search / find-in-page inputs

> **Note:** When a web element mode is selected, pressing Up/Down arrows sends the corresponding quick-nav key (e.g. `H` for headings, `K` for links), causing NVDA to jump to the previous/next matching element in the page. This is identical to pressing those keys in NVDA's browse mode, but without needing to hold a modifier.

#### Smart Features & Customization
- **Auto-Exit (Timeout):** If left idle for 10 seconds, the layer automatically exits with a soft audio cue so you are never trapped inside.
- **Key Pass-through:** Pressing any key not bound to the layer (e.g., Windows key) will immediately exit the layer and pass the keypress to the OS seamlessly.
- **Full Customization (Settings Tab 6):** You can enable or disable any of the 27 modes to keep your mode-cycling clutter-free, adjust layer timeout, and configure action sounds.

### 2. Audio Sonar
- **Shortcut:** `NVDA+Alt+R` (or `NVDA+Shift+A` then `r`)
- **Description:** An incredible feature that sweeps the entire active window, collects all controls inside it (buttons, lists, texts), and rapidly plays their associated sounds from left to right in 3D space. This gives you a sonic "picture" of the window's layout and how populated it is!

### 3. Audio Beacon
- **Shortcut:** `NVDA+Shift+B` (or `NVDA+Shift+A` then `a`)
> **Note:** `NVDA+Shift+B` is NVDA's standard battery status command in all keyboard layouts. If you use this shortcut for battery announcements, use the alternative sequence `NVDA+Shift+A` then `a` to activate the beacon instead.
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
| **Ctrl+C / X / V** | Copy, Cut, and Paste with audio announcements. |
| **Ctrl+A** | Select All with audio announcement. |
| **Ctrl+Z / Y** | Undo and Redo with audio announcements. |
| **Ctrl+Shift+V** | Paste plain text with audio announcement. |
| **Ctrl+Shift+Z** | Alternate redo with audio announcement. |

## Compatibility & Requirements
- **NVDA Version:** Requires NVDA 2024.1.0 or later.
- **Last Tested NVDA Version:** 2026.2.0
- **Operating System:** Windows 10 or Windows 11.

## Source Code & Repository
You can view the source code, report issues, or contribute to the project on GitHub:
[Advanced Audio Themes Repository](https://github.com/HassanAlBarshoumy/advanced_audio_themes)

## Change Log

### Version 9.34
- **Critical Bug Fix — Gesture Binding Corruption:** Fixed a severe issue where all addon and user-assigned keyboard shortcuts (e.g. `NVDA+Alt+P` from NVDAExtensionGlobalPlugin) would break and disappear from the Input Gestures dialog after opening and closing either the Audio Themes Command Layer (`NVDA+Shift+A`) or the Navigation Layer (`NVDA+Win+N`). The root cause was `clearGestureBindings()` + `_rebindInstanceGestures()` being called on every layer deactivation, which wiped all entries from NVDA's internal `boundGestures` map. Replaced with targeted `removeGestureBinding()` calls per-layer and a suppression flag for gesture execution — `boundGestures` is never touched during layer open/close cycles.
- **Navigation Layer Documentation:** Expanded the Navigation Layer section in this readme to include a complete reference table of all layer controls and a detailed list of all 27 navigation modes with descriptions.
- **Startup Logging:** Added an INFO-level log entry at add-on initialization to record the loaded version in the NVDA log.

### Version 9.33
- **Emoji Enhancement Engine:** A brand-new emoji detection and enhancement system powered by Unicode CLDR data. Emojis are automatically detected in speech and can play unique sounds per category (Smileys, People, Animals, Food, Travel, Activities, Objects, Symbols, Flags). Includes configurable speech prefix/suffix, per-emoji or per-block repeat, volume control, delay timing, category-based toggles, blacklisting, custom descriptions, and role sound suppression. Full settings GUI with a dedicated "Emoji" tab.
- **Clipboard Announcements:** A new clipboard feedback system that plays sounds and speaks confirmations for Copy, Cut, Paste, Select All, Undo, Redo, and Paste Plain Text. Each action can be individually configured with custom announcement text, toggled sound/speech, and adjustable delay. Full settings GUI with a dedicated "Clipboard" tab.
- **New Built-in Theme:** Added the "HAS Future Sound" audio theme with a fresh set of modern sounds.
- **ZIP Theme Import Fix:** Fixed a bug where importing a ZIP theme without an `info.json` file would leave a UUID-named folder instead of using the theme's filename.
- **System Status Hardening:** Extensive Win32 fixes for 64-bit systems including proper `argtypes` for all user32 functions, correct `DEV_BROADCAST_VOLUME` struct usage, and reliable device notification registration.
- **Performance:** Optimized emoji and symbol processing with CLDR index caching for near-zero overhead.
- **Input Gestures:** 6 scripts that previously had no default gestures now appear in NVDA's Input Gestures dialog, allowing users to assign custom shortcuts.

### Version 9.32
- **System Status Sounds:** Added a completely new module to monitor and play sounds for system-level events (USB plug/unplug, AC power changes, battery status, network connectivity, and system wake/sleep) using native Windows notifications for zero lag.
- **Audio DSP Enhancements:** Completely rewrote the Bass Boost (Low-shelf filter) and Noise Gate algorithms to support correct attack/release times and improved sound quality. Added a full UI in the settings panel to control these DSP effects.
- **3D Spatial Audio Fixes:** Resolved an issue causing lag in 3D audio playback for progress bars.

### Version 9.30 - 9.31
- **Universal First/Last Item Detection:** Added support for first/last item detection for *all* NVDA roles, instead of just lists and menus.
- **Advanced Detection Modes:** Introduced 3 detection modes (smart, strict, any_sibling) with multi-hop traversal to guarantee accurate detection of the first and last elements even in complex web layouts.

### Version 9.27 - 9.28
- **Role vs State Sounds Priority:** Fixed an issue where state sounds (like "checked") were wrongly suppressing role sounds (like "checkbox").
- **Fallback Behaviors:** Added custom fallback settings for first/last item sounds, allowing users to select custom sounds or bypass missing roles.
- **Heading Support:** Added support for Heading levels 7, 8, and 9.

### Version 9.23 - 9.26
- **Sentence Navigation Fixes:** Fixed a bug causing NVDA to endlessly repeat sentences when reading Arabic text in VirtualBuffers.
- **NVDA 2026.2 Compatibility:** Migrated to the new `NVDAHelper.localLib.generateBeep` API to resolve deprecation warnings and ensure stability on future NVDA versions.
- **Auto-Update Fix:** Resolved a critical freeze in NVDA during the auto-update download process.

### Version 9.21 - 9.22
- **Import Enhancements:** Added support for importing uncompressed folders as themes, and a dialog to choose between importing a folder or ZIP/.atp file.
- **Auto-Update & Pre-release:** Added checkboxes in the General tab to handle auto-updates and opt into pre-release beta builds.

### Version 9.20
- **Settings UI Optimization:** Major performance improvements to the Settings dialog. Replaced slow grids with fast ListCtrls and implemented lazy-loading for all heavy tabs.
- **Theme Caching:** Cached installed themes to reduce file I/O on startup.

### Version 9.11 - 9.13
- **Conflict Detection:** Added a smart startup dialog that detects conflicting NVDA add-ons (like older audio themes plugins) and allows the user to disable or uninstall them safely.

### Version 9.4 - 9.10
- **Native MP3 Decoding:** Integrated libmpg123 for fast, native MP3 decoding without relying entirely on FFmpeg.
- **Audio Processing Pipeline:** Added OGG RAM caching, 24-bit WAV support, and completely migrated audio DSP features (SmartVolume, Envelope, TrimSilence) to the new pipeline.
- **Translations:** Completed 100% full localization for Arabic, Spanish, Italian, Russian, German, and Chinese.

## Translators

- **Arabic:** Hassan AlBarshoumy
- **Spanish:** Hassan AlBarshoumy, Luis Carlos González Morales
- **Italian:** Christian Cantelmi, Ciro Cantelmi
- **Russian:** Valentin Kupriyanov
- **Chinese:** Cary-rowen, Jerry
- **German:** René L

## Support

For any issues, requests, or bug reports, please refer to the official contact point:
**[Hassan AlBarshoumy's Telegram](https://t.me/HassanAlBarshoumy)**
