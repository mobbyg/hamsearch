![hamsearch](https://github.com/mobbyg/hamsearch/assets/5174814/69ce0da3-ce40-4c18-94de-83a388ce6c2f)

# HamSearch

HamSearch is a Mystic BBS add-on for looking up amateur radio callsigns using FCC ULS data.

It is designed to run inside Mystic BBS as a Python 3 MPY script and display callsign lookup results directly to the user from within the BBS.

---

## Features

- Callsign search from inside Mystic BBS
- Uses FCC ULS amateur data
- Supports a local SQLite database for faster lookups
- Falls back to flat FCC data files if needed
- Shows:
  - callsign
  - operator class
  - license status
  - grant / expiration / cancellation dates when available
  - name and mailing address
  - previous callsign references when available
  - recent history entries when available
- Includes a helper script to:
  - download the FCC ZIP file
  - extract required data files
  - build the SQLite database

---

## Included Files

- `hamserach.mpy` - Mystic Python 3 search script
- `getdb.py` - FCC downloader / extractor / SQLite builder
- `hshdr.ans` - ANSI header/display file
- `install.txt` - install instructions

---

## Requirements

- Mystic BBS with Python 3 MPY support
- Python 3 on the host system for `getdb.py`
- Internet access on the host system to download FCC data
- Sufficient disk space for FCC data files and SQLite database

---

## How It Works

`getdb.py` downloads the current FCC amateur ULS ZIP archive, extracts the needed data files into the `data/` directory, and builds `hamsearch.db`.

`hamserach.mpy` then uses that SQLite database for lookups. If SQLite is not available, it can still fall back to the FCC flat files.

---

## FCC Data Used

The project is intended to work with the amateur data from the FCC ULS public database download.

The current builder is set up to work with these files when present:

- `AM.dat`
- `EN.dat`
- `HD.dat`
- `HS.dat`

These are used to provide current callsign details, class and status data, and some historical references such as previous callsigns and status history.

---

## Installation

See `install.txt` for step-by-step setup instructions.

---

## Current Status

This project is still evolving, but the current direction is focused on:

- better data management
- better formatting
- better history handling
- more complete FCC record support
- cleaner Mystic integration

---

## Planned Improvements

- Better menu system
- Better result formatting
- About/info screen with database build date
- More advanced search options
- Better handling of historical callsign data
- Better handling of silent key related status/history records
- Logging and maintenance tools

---

## Notes for Contributors

If you contribute to this project, please comment your code clearly so newer programmers and Mystic sysops can understand what is happening.

Keeping the code readable and well-documented is important.

---

## Thanks

73!

**MobbyG / KB2MOB**  
SysOp of Radio Freqs & Geeks BBS
