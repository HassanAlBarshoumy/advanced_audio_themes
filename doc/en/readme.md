# Audio Themes NG & Phonetic Punctuation

This add-on provides an immersive audio experience for NVDA screen reader users by playing sounds for various UI events. It allows for the creation, installation, and customization of audio themes, enhancing the auditory feedback from the user interface.

## Features

- **Audio effects:** Plays sounds for UI events such as focusing on controls, navigating lists, and more.
- **3D Audio:** Utilizes Steam Audio to provide 3D positional audio, giving a sense of where controls are on the screen.
- **Reverb:** Adds reverb effects to the audio for a more immersive experience.
- **Customizable Themes:** Allows users to create, install, and switch between different audio themes.
- **Audio Themes Studio V2:** A built-in tool to create new audio themes or edit existing ones directly from the microphone or via drag & drop.
- **Advanced Typing Sounds:** Simulates physical keyboard typing with spatial audio positioning, dynamic velocity volume adjustments, and smart key mapping for special keys (Enter, Backspace, Space, Shift, Ctrl, Alt).
- **Audio Beacon / Sonar:** Drop a spatial audio beacon at any location on the screen and navigate around to hear real-time sonar pings guiding you relative to the beacon.
- **Advanced Navigation:** Integrated SentenceNav and BrowserNav engines for seamless text and web navigation without conflicting arrow keys.

## Development & Credits

This add-on is the result of merging and consolidating multiple open-source projects in the NVDA community:

* **Hassan AlBarshoumy:** Main developer and consolidator of the current unified version (Advanced Audio Themes), including the Audio Themes Studio and unified settings.
* **Ahmed Sami:** Special thanks and acknowledgements for assistance, support, and contributions.
* **Musharraf Omer:** Original developer of the Audio Themes 3D add-on.
* **Tony Malykh:** Original developer of the Earcons and Speech Rules, BrowserNav, and SentenceNav add-ons.
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

In the "Audio Themes" settings panel, you can:

- **Select a theme:** Choose from the list of installed audio themes.
- **Add a new theme:** Click the "Add New..." button to install a theme from an `.atp` file.
- **Remove a theme:** Select a theme and click the "Remove" button.
- **About a theme:** Click the "About" button to see information about the selected theme.

### Using the Audio Themes Studio V2

The Audio Themes Studio allows you to create and edit audio themes. To open the studio:

1. Open the NVDA menu (NVDA+N).
2. Select "Audio Themes Studio".

In the studio, you can:

- **Create a new audio theme:** This will guide you through the process of creating a new theme from scratch.
- **Customize an existing audio theme:** Select this option to modify the sounds of an installed theme.
- **Record from Microphone:** You can now natively record your voice or any sound directly from your microphone to be assigned to a UI event!
- **Drag & Drop:** You can drag and drop audio files directly into the Studio window to assign them rapidly.

### Exporting Your Theme

After creating or editing a theme, you can export it as an `.atp` file to share it with others. You can find the export option in the editing screen.

## Advanced Rules & Phonetic Punctuation

Earcons and Speech Rules allow NVDA to play earcons as well as other speech effects, such as prosody changes.

### Usage
1. Make sure the add-on is enabled. Press NVDA+Alt+P to toggle it.
2. Rules can be configured via a dialog box in NVDA preferences menu.
3. By default you will have a set of predefined audio rules.
4. The rules are saved in a file called `earconsAndSpeechRules.json` in your NVDA user configuration directory.

### Keyboard Commands

* **NVDA+Alt+N:** Toggle Audio Themes on/off. Press twice quickly to toggle Typing Sounds.
* **NVDA+Alt+T:** Cycle through available Audio Themes.
* **NVDA+Alt+Y:** Cycle through available Typing Sound packs.
* **NVDA+Alt+K:** Toggle Typing Sounds on/off.
* **NVDA+Shift+B:** Drop/Remove an Audio Beacon at the current navigator object.
* **NVDA+Shift+A:** Enter Audio Themes Command Layer (press this, then a command key such as 'h' for help, 't' to toggle themes, 'p' to toggle rules, 's' to toggle state verbosity, 'c' to speak heading level, 'o' to rotate speech order).
* **NVDA+Alt+P:** Toggle earcons and sound speech rules add-on.
* **NVDA+Alt+[ (left bracket):** Toggle concise state reporting mode.
* **NVDA+H:** Speak current heading level.
* **NVDA+Tab:** Report the object under the cursor with full 3D audio coordinates.
* **Alt+Arrows:** Advanced Sentence/Phrase Navigation.
* **NVDA+Alt+Arrows:** Advanced Web Navigation (BrowserNav).

## Support

For any issues, requests, or bug reports, please refer to the official contact point:
**[Hassan AlBarshoumy's Telegram](https://t.me/HassanAlBarshoumy)**
