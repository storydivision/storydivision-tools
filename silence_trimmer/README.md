# Silence Trimmer

Automatically trim silence from video and audio files and save as MP3. Works with MP4 and MP3 input files on Linux and macOS.

## Features

- 🎬 Process MP4 videos and MP3 audio files
- 🔇 Intelligent silence detection and removal
- 📁 Batch process entire directories
- ⚙️ Customizable silence thresholds and padding
- 📊 Shows time saved and compression stats
- 🚀 Works with `uv` for fast execution
- 🎯 Two modes: safe (trim start/end only) or aggressive (remove all silence)
- 🎵 Outputs both MP3 and lossless (WAV/AIFF) by default

## Prerequisites

**ffmpeg** must be installed:

```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# Linux (Fedora)
sudo dnf install ffmpeg
```

## Installation

No installation required! Just run the script with Python or uv.

### Option 1: Direct Python (simplest)

```bash
# Make executable (optional)
chmod +x trim_silence.py

# Run directly
python trim_silence.py video.mp4
```

### Option 2: Using uv (recommended for dependency management)

[uv](https://github.com/astral-sh/uv) is a fast Python package installer and resolver.

```bash
# Run directly with uv (creates virtual environment automatically)
uv run trim_silence.py video.mp4

# Or install as a tool
uv tool install .
trim-silence video.mp4
```

## Usage

### Basic Examples

```bash
# Process a single file (uses defaults)
python trim_silence.py video.mp4
# Or with uv:
uv run trim_silence.py video.mp4

# Process all files in a directory
python trim_silence.py -d ./videos

# Process with custom output directory
python trim_silence.py video.mp4 -o ./processed
```

### Advanced Examples

```bash
# More aggressive threshold (stricter silence detection)
python trim_silence.py video.mp4 -t -50

# Less aggressive (keeps more audio)
python trim_silence.py video.mp4 -t -30

# Aggressive mode: remove silence throughout (not just start/end)
python trim_silence.py video.mp4 --aggressive -m 0.6

# High quality output
python trim_silence.py video.mp4 -b 320k

# Verbose mode to see ffmpeg output
python trim_silence.py video.mp4 -v

# Output AIFF instead of WAV
python trim_silence.py video.mp4 --lossless aiff

# Skip lossless output (MP3 only)
python trim_silence.py video.mp4 --lossless none
```

## Options

```text
positional arguments:
  input_file            Input file (MP4 or MP3)

optional arguments:
  -h, --help            Show help message
  -d, --directory DIR   Process all MP4/MP3 files in directory
  -o, --output DIR      Output directory (default: creates 'trimmed_output' in source location)
  
Silence Detection:
  -t, --threshold DB    Silence threshold in dB (default: -30)
                        Lower = stricter. Try -30 to -50
  -m, --min-duration S  Minimum silence duration in seconds (default: 0.2)
                        Only used in aggressive mode
  -p, --padding S       Padding to keep around speech in seconds (default: 0.1)
  
Quality:
  -b, --bitrate RATE    Output MP3 bitrate (default: 128k)
                        Options: 128k, 192k, 320k
  --lossless FORMAT     Lossless format alongside MP3 (default: wav)
                        Options: wav, aiff, none
  
Other:
  -a, --aggressive      Remove silence throughout audio (default: only trim start/end)
                        WARNING: May cut into speech!
  -v, --verbose         Show detailed ffmpeg output
```

## Default Settings

The defaults work well for 80% of use cases:

- **Mode**: Safe (only trims silence from start and end)
- **Silence threshold**: -30dB (catches background noise and rustling)
- **Min silence duration**: 0.2 seconds (only used in aggressive mode)
- **Padding**: 0.1 seconds (keeps natural flow)
- **MP3 bitrate**: 128kbps (good quality/size balance)
- **Lossless output**: WAV (full quality alongside MP3)

## Modes

### Safe Mode (Default)

Only removes silence from the **beginning and end** of the audio. Preserves all natural pauses in speech. Best for most use cases.

### Aggressive Mode (`--aggressive`)

Removes silence **throughout** the entire audio using FFmpeg's multi-command approach:

1. Detects all silence periods with `silencedetect`
2. Extracts non-silent segments
3. Concatenates them back together

The `-m` flag controls which silences are removed:

- Only silences **longer than** the `-m` value are removed
- Shorter silences are left untouched
- This preserves natural speech rhythm

**Important**: Start with `-m 0.6` or higher to avoid removing natural pauses:

```bash
# Remove only long pauses (>0.6s) - matches Premiere Pro behavior
python trim_silence.py video.mp4 --aggressive -m 0.6

# More aggressive (>0.4s)
python trim_silence.py video.mp4 --aggressive -m 0.4
```

## Tuning Tips

### If too much audio is removed (dialog is cut off)

- Use safe mode (default, no `--aggressive` flag)
- Increase threshold: `-t -25` (less strict, keeps more audio)
- In aggressive mode, increase min duration: `-m 0.7` (only remove longer pauses)

### If not enough silence is removed

- Decrease threshold: `-t -40` (more strict, removes more)
- Try aggressive mode: `--aggressive -m 0.6` (removes long pauses throughout)
- For very aggressive removal: `--aggressive -m 0.4` (use carefully!)

## Output

Processed files are saved to a `trimmed_output` folder in the source directory with `_trimmed` suffix. By default, both MP3 and WAV files are created.

Example output:

```text
Processing: video.mp4
  ✓ MP3 saved to: trimmed_output/video_trimmed.mp3
  ✓ WAV saved to: trimmed_output/video_trimmed.wav
  ✓ Original: 120.5s → Trimmed: 95.3s
  ✓ Removed 25.2s of silence (20.9%)
```

## How It Works

### Safe Mode (Default)
Uses FFmpeg's `silenceremove` filter to trim silence from start and end only.

### Aggressive Mode
Uses a multi-step FFmpeg approach:

1. **Detect**: Uses `silencedetect` to find all silence periods
2. **Extract**: Cuts out non-silent segments with `-c copy` (fast!)
3. **Concatenate**: Joins segments back together
4. **Export**: Outputs as MP3 and lossless WAV/AIFF

## License

Free to use and modify for any purpose.
