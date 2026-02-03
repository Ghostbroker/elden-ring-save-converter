#!/usr/bin/env python3
"""
Elden Ring Save Converter

Converts Elden Ring save files (.sl2 or .co2) from one Steam ID to another
by replacing the Steam ID and recalculating all checksums.

Supports:
  - Vanilla Elden Ring saves (.sl2)
  - Seamless Coop mod saves (.co2)

Usage:
    python convert_save.py <save_file> <new_steam_id> [output_file]

Example:
    python convert_save.py ER0000.co2 76561198012345678
    python convert_save.py ER0000.sl2 76561198012345678 converted.sl2
"""

import argparse
import hashlib
import struct
import sys
from pathlib import Path
from enum import Enum


class SaveType(Enum):
    VANILLA = "vanilla"
    SEAMLESS_COOP = "seamless_coop"


# Save file structure constants
SLOT_DATA_LENGTH = 2621440      # 0x280000 bytes per slot
SLOT_STRIDE = 2621456           # 0x280010 bytes between slot starts
SLOT_COUNT = 10                 # 10 character slots (0-9)

# Offsets for character slots (same for both formats)
FIRST_SLOT_CHECKSUM = 0x300
FIRST_SLOT_DATA = 0x310

# Seamless Coop specific: Slot 10 (general metadata)
COOP_GENERAL_CHECKSUM_START = 0x019003A0
COOP_GENERAL_CHECKSUM_END = 0x019003B0
COOP_GENERAL_DATA_START = 0x019003B0
COOP_GENERAL_DATA_END = 0x019603B0

# Vanilla specific: Slot 10 (general data) - different structure
VANILLA_GENERAL_CHECKSUM_START = 0x019003A0
VANILLA_GENERAL_CHECKSUM_END = 0x019003B0
VANILLA_GENERAL_DATA_START = 0x019003B0
VANILLA_GENERAL_DATA_END = 0x01901BB0  # 0x1800 bytes (6144 bytes)

# File size thresholds for detection
VANILLA_FILE_SIZE = 26_214_400      # ~25 MB
SEAMLESS_COOP_FILE_SIZE = 28_967_888  # ~27.6 MB


def detect_save_type(data: bytes, file_path: Path | None = None) -> SaveType:
    """Detect whether this is a vanilla or Seamless Coop save."""
    # Check by file extension first
    if file_path:
        suffix = file_path.suffix.lower()
        if suffix == '.sl2':
            return SaveType.VANILLA
        elif suffix == '.co2':
            return SaveType.SEAMLESS_COOP

    # Fall back to file size detection
    file_size = len(data)
    if file_size >= SEAMLESS_COOP_FILE_SIZE - 1000:
        return SaveType.SEAMLESS_COOP
    else:
        return SaveType.VANILLA


def find_steam_ids(data: bytes) -> list[tuple[int, int]]:
    """
    Find all potential Steam IDs in the save file.
    Returns list of (offset, steam_id) tuples.
    """
    found = []

    # Search for 8-byte sequences that look like Steam IDs
    for i in range(0, len(data) - 8, 4):  # Align to 4-byte boundary
        val = struct.unpack('<Q', data[i:i + 8])[0]
        # Steam IDs are in range 76561197960265728 to ~76561199999999999
        if 76561197960265728 <= val <= 76561199999999999:
            found.append((i, val))

    return found


def get_primary_steam_id(data: bytes, save_type: SaveType) -> int | None:
    """Get the primary Steam ID from the save file."""
    if save_type == SaveType.SEAMLESS_COOP:
        # Seamless Coop stores Steam ID at fixed offset in general section
        steam_id_offset = 0x019003B4
        if steam_id_offset + 8 <= len(data):
            steam_id = struct.unpack('<Q', data[steam_id_offset:steam_id_offset + 8])[0]
            if 76561197960265728 <= steam_id <= 76561199999999999:
                return steam_id

    # For vanilla or if Seamless Coop offset didn't work, search for Steam IDs
    found = find_steam_ids(data)
    if found:
        # Return the most common Steam ID (in case there are multiple)
        from collections import Counter
        id_counts = Counter(steam_id for _, steam_id in found)
        return id_counts.most_common(1)[0][0]

    return None


def replace_steam_id(data: bytearray, old_id: int, new_id: int) -> list[int]:
    """Replace all occurrences of the old Steam ID with the new one."""
    old_bytes = struct.pack('<Q', old_id)
    new_bytes = struct.pack('<Q', new_id)

    locations = []
    offset = 0

    while True:
        pos = data.find(old_bytes, offset)
        if pos == -1:
            break
        data[pos:pos + 8] = new_bytes
        locations.append(pos)
        offset = pos + 8

    return locations


def recalculate_checksums(data: bytearray, save_type: SaveType) -> None:
    """Recalculate all checksums in the save file."""
    # Recalculate slots 0-9 (same for both formats)
    for slot in range(SLOT_COUNT):
        checksum_offset = FIRST_SLOT_CHECKSUM + (slot * SLOT_STRIDE)
        data_start = FIRST_SLOT_DATA + (slot * SLOT_STRIDE)
        data_end = data_start + SLOT_DATA_LENGTH

        slot_data = data[data_start:data_end]
        new_checksum = hashlib.md5(slot_data).digest()
        data[checksum_offset:checksum_offset + 16] = new_checksum

    # Recalculate slot 10 (general) - different range depending on save type
    if save_type == SaveType.SEAMLESS_COOP:
        general_data = data[COOP_GENERAL_DATA_START:COOP_GENERAL_DATA_END]
        new_checksum = hashlib.md5(general_data).digest()
        data[COOP_GENERAL_CHECKSUM_START:COOP_GENERAL_CHECKSUM_END] = new_checksum
    else:
        # Vanilla save - slot 10 has different data range
        general_data = data[VANILLA_GENERAL_DATA_START:VANILLA_GENERAL_DATA_END]
        new_checksum = hashlib.md5(general_data).digest()
        data[VANILLA_GENERAL_CHECKSUM_START:VANILLA_GENERAL_CHECKSUM_END] = new_checksum


def validate_checksums(data: bytes, save_type: SaveType) -> list[tuple[int, bool]]:
    """Validate all checksums and return results."""
    results = []

    # Check slots 0-9
    for slot in range(SLOT_COUNT):
        checksum_offset = FIRST_SLOT_CHECKSUM + (slot * SLOT_STRIDE)
        data_start = FIRST_SLOT_DATA + (slot * SLOT_STRIDE)
        data_end = data_start + SLOT_DATA_LENGTH

        stored = data[checksum_offset:checksum_offset + 16]
        computed = hashlib.md5(data[data_start:data_end]).digest()
        results.append((slot, stored == computed))

    # Check slot 10
    if save_type == SaveType.SEAMLESS_COOP:
        stored = data[COOP_GENERAL_CHECKSUM_START:COOP_GENERAL_CHECKSUM_END]
        computed = hashlib.md5(data[COOP_GENERAL_DATA_START:COOP_GENERAL_DATA_END]).digest()
    else:
        stored = data[VANILLA_GENERAL_CHECKSUM_START:VANILLA_GENERAL_CHECKSUM_END]
        computed = hashlib.md5(data[VANILLA_GENERAL_DATA_START:VANILLA_GENERAL_DATA_END]).digest()
    results.append((10, stored == computed))

    return results


def validate_steam_id(steam_id_str: str) -> int:
    """Validate and parse a Steam ID string."""
    # Remove any whitespace
    steam_id_str = steam_id_str.strip()

    try:
        steam_id = int(steam_id_str)
    except ValueError:
        raise ValueError(f"Steam ID must be a number, got: {steam_id_str}")

    if not (76561197960265728 <= steam_id <= 76561199999999999):
        raise ValueError(f"Invalid Steam ID format: {steam_id}")

    return steam_id


def convert_save(
    file_path: Path,
    new_steam_id: int,
    output_path: Path | None = None,
    callback=None
) -> dict:
    """
    Convert a save file to use a new Steam ID.

    Args:
        file_path: Path to the source save file
        new_steam_id: The new Steam ID to use
        output_path: Optional output path (defaults to overwriting source)
        callback: Optional callback function for progress updates

    Returns:
        dict with conversion results
    """
    def log(msg):
        if callback:
            callback(msg)
        else:
            print(msg)

    # Read the file
    with open(file_path, 'rb') as f:
        data = bytearray(f.read())

    # Detect save type
    save_type = detect_save_type(data, file_path)
    log(f"Detected save type: {save_type.value}")

    # Find current Steam ID
    old_steam_id = get_primary_steam_id(data, save_type)
    if old_steam_id is None:
        raise ValueError("Could not find a valid Steam ID in the save file")

    if old_steam_id == new_steam_id:
        raise ValueError(f"Save file already uses Steam ID {new_steam_id}")

    log(f"Current Steam ID: {old_steam_id}")
    log(f"New Steam ID: {new_steam_id}")

    # Replace Steam ID
    locations = replace_steam_id(data, old_steam_id, new_steam_id)
    log(f"Replaced Steam ID at {len(locations)} location(s)")

    # Recalculate checksums
    recalculate_checksums(data, save_type)
    log("Recalculated all checksums")

    # Determine output path
    if output_path is None:
        output_path = file_path

    # Write the modified file
    with open(output_path, 'wb') as f:
        f.write(data)

    log(f"Save file written to: {output_path}")

    return {
        'save_type': save_type,
        'old_steam_id': old_steam_id,
        'new_steam_id': new_steam_id,
        'locations_modified': locations,
        'output_path': output_path
    }


def main():
    parser = argparse.ArgumentParser(
        description="Convert Elden Ring saves (.sl2 or .co2) to a different Steam ID"
    )
    parser.add_argument(
        "save_file",
        type=Path,
        help="Path to the save file (.sl2 or .co2)"
    )
    parser.add_argument(
        "new_steam_id",
        type=str,
        help="Your Steam ID (17-digit number)"
    )
    parser.add_argument(
        "output_file",
        type=Path,
        nargs='?',
        default=None,
        help="Output file path (optional, defaults to overwriting source)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Only validate checksums, don't convert"
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.save_file.exists():
        print(f"Error: File not found: {args.save_file}", file=sys.stderr)
        sys.exit(1)

    # Validation-only mode
    if args.validate:
        with open(args.save_file, 'rb') as f:
            data = f.read()
        save_type = detect_save_type(data, args.save_file)
        print(f"Save type: {save_type.value}")
        print(f"Checksum validation:")
        for slot, valid in validate_checksums(data, save_type):
            status = "✓" if valid else "✗"
            print(f"  Slot {slot}: {status}")
        sys.exit(0)

    try:
        new_steam_id = validate_steam_id(args.new_steam_id)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert the save
    try:
        result = convert_save(args.save_file, new_steam_id, args.output_file)
        print(f"\nConversion successful!")
        print(f"  Save type: {result['save_type'].value}")
        print(f"  Steam ID: {result['old_steam_id']} -> {result['new_steam_id']}")
        print(f"  Locations modified: {len(result['locations_modified'])}")
        print(f"  Output: {result['output_path']}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
