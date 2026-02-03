# Elden Ring Save Converter

Convert Elden Ring save files between Steam accounts by replacing the Steam ID and recalculating checksums.

**Supports:**
- Vanilla Elden Ring saves (`.sl2`)
- Seamless Coop mod saves (`.co2`)

## Requirements

- Python 3.10 or later
- tkinter (included with Python on Windows/macOS, may need `python3-tk` package on Linux)

### Optional (for drag and drop support)
```bash
pip install tkinterdnd2
```

## Usage

### GUI Version (Recommended)

```bash
python convert_save_gui.py
```

1. Select or drag and drop your save file
2. Enter your Steam ID (17-digit number starting with 7656119...)
3. Choose where to save the converted file
4. Click "Convert Save"

### Command Line Version

```bash
# Basic usage (overwrites original)
python convert_save.py <save_file> <your_steam_id>

# Save to a new file
python convert_save.py <save_file> <your_steam_id> <output_file>

# Validate checksums only
python convert_save.py <save_file> dummy --validate
```

**Examples:**
```bash
python convert_save.py ER0000.co2 76561198012345678
python convert_save.py ER0000.sl2 76561198012345678 converted.sl2
```

## Finding Your Steam ID

1. Open Steam and go to your profile
2. Right-click and select "Copy Page URL"
3. The URL contains your Steam ID: `https://steamcommunity.com/profiles/76561198XXXXXXXXX`

Or use [steamid.io](https://steamid.io) with your Steam username.

## How It Works

Elden Ring saves store your Steam ID in multiple locations within the file. The game validates the save using MD5 checksums for each character slot.

This tool:
1. Finds and replaces all occurrences of the original Steam ID
2. Recalculates all 11 checksums (10 character slots + 1 general section)
3. Saves the modified file

## Save File Locations

| Platform | Location |
|----------|----------|
| Windows | `%AppData%\EldenRing\<SteamID>\` |
| Linux (Proton) | `~/.steam/steam/steamapps/compatdata/1245620/pfx/drive_c/users/steamuser/AppData/Roaming/EldenRing/<SteamID>/` |

- Vanilla saves: `ER0000.sl2`
- Seamless Coop saves: `ER0000.co2`

## Disclaimer

- Always back up your save files before modifying them
- Use at your own risk
- This tool is for legitimate save transfers (e.g., sharing saves with friends)
- Modifying save files may violate game terms of service

## Credits

Checksum algorithm based on research from the [EldenRing-Save-Manager](https://github.com/Ariescyn/EldenRing-Save-Manager) project.
