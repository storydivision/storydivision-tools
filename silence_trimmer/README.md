# Silence Trimmer

A Python wrapper for ffmpeg that automatically trims silence from video and audio files. This tool uses ffmpeg's silence detection and removal filters to analyze and trim silence where it exists. Works with all common audio and video formats that ffmpeg supports on Linux and macOS.

## Features

- 🎬 Process all common video formats (MP4, MKV, AVI, MOV, WebM, FLV, etc.)
- 🎵 Process all common audio formats (MP3, M4A, FLAC, WAV, AAC, OGG, OPUS, etc.)
- 🔇 Intelligent silence detection and removal
- 📁 Batch process entire directories
- ⚙️ Customizable silence thresholds and padding
- 📊 Shows time saved and compression stats
- 🚀 Works with `uv` for fast execution
- 🎯 Two modes: safe (trim start/end only) or aggressive (remove all silence)
- 🎵 Outputs both MP3 and lossless (WAV/AIFF) by default

## Supported Formats

This tool supports all common audio and video formats that ffmpeg can process:

**Video formats:** MP4, MKV, AVI, MOV, WMV, FLV, WebM, M4V, MPG, MPEG, 3GP, OGV, TS, MTS, M2TS, VOB, ASF, RM, RMVB, DivX

**Audio formats:** MP3, M4A, AAC, WAV, FLAC, OGG, OPUS, WMA, AIFF, APE, AC3, DTS, ALAC, AMR, AU, CAF, MKA, OGA, RA, WV, TTA, TAK, MPC, DSF, DFF

All files are processed and output as MP3 (plus optional lossless WAV/AIFF).

## Prerequisites

**ffmpeg** must be installed:

```bash
# macOS
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt install ffmpeg

# Linux (Fedora)
sudo dnf install ffmpeg

# Conda (any platform)
conda install -c conda-forge ffmpeg
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
python trim_silence.py video.mp4 -l aiff

# Skip lossless output (MP3 only)
python trim_silence.py video.mp4 -l none

# Normalize speech levels before trimming (uses loudnorm by default)
python trim_silence.py audio.m4a --normalize
# Or shorthand:
python trim_silence.py audio.m4a -n

# Use dynamic normalization (faster)
python trim_silence.py audio.m4a -n dynaudnorm

# JSON output for parsing by other tools
python trim_silence.py video.mp4 -j
```

## Options

```text
positional arguments:
  input_file            Input audio or video file (supports most common formats)

optional arguments:
  -h, --help            Show help message
  -d, --directory DIR   Process all supported audio/video files in directory
  -o, --output DIR      Output directory (default: creates 'trimmed_output' in source location)
  
Silence Detection:
  -t, --threshold DB    Silence threshold in dB (default: -30)
                        Lower = stricter. Try -30 to -50
  -m, --min-duration S  Minimum silence duration in seconds (default: 0.2)
                        Only used in aggressive mode
  -p, --padding S       Padding to keep around speech in seconds (default: 0.2)
  
Quality:
  -b, --bitrate RATE    Output MP3 bitrate (default: 128k)
                        Options: 128k, 192k, 320k
  -l, --lossless FORMAT Lossless format alongside MP3 (default: wav)
                        Options: wav, aiff, none
  
Other:
  -a, --aggressive      Remove silence throughout audio (default: only trim start/end)
                        WARNING: May cut into speech!
  -n, --normalize [METHOD]
                        Apply audio normalization before silence detection.
                        Options: loudnorm (default, EBU R128 standard),
                                 dynaudnorm (faster, dynamic)
                        Use -n alone for loudnorm, or -n dynaudnorm
                        Recommended for speech/voice content
  -v, --verbose         Show detailed ffmpeg output
  -j, --json            Output results as JSON to STDOUT (suppresses all other output)
```

## Default Settings

The defaults work well for 80% of use cases:

- **Mode**: Safe (only trims silence from start and end)
- **Silence threshold**: -30dB (catches background noise and rustling)
- **Min silence duration**: 0.2 seconds (only used in aggressive mode)
- **Padding**: 0.2 seconds (keeps natural flow and prevents cutting word endings)
- **MP3 bitrate**: 128kbps (good quality/size balance)
- **Lossless output**: WAV (full quality alongside MP3)

## Audio Normalization

The `--normalize` (or `-n`) flag applies audio normalization **before** silence detection. This is highly recommended for speech/voice content because:

- **Consistent levels**: Normalizes volume across the entire recording
- **Better silence detection**: Makes it easier to distinguish speech from silence
- **Professional sound**: Evens out quiet and loud sections

### Normalization Methods

**`loudnorm` (Default - Recommended)**

- EBU R128 loudness normalization standard
- **Optimized for streaming platforms** (YouTube, Spotify, etc.)
- Targets **-16 LUFS** (competitive with typical YouTube videos)
- Much louder than broadcast standard (-24 LUFS)
- Best for: YouTube, podcasts, social media, any online content
- Usage: `-n` or `-n loudnorm`

**`dynaudnorm` (Alternative)**

- Dynamic audio normalizer
- Faster processing, simpler algorithm
- Best for: Quick processing, general use
- Usage: `-n dynaudnorm`

**Examples:**

```bash
# Use loudnorm (default, best for speech)
python trim_silence.py interview.m4a -n

# Explicitly specify loudnorm
python trim_silence.py interview.m4a -n loudnorm

# Use dynaudnorm (faster)
python trim_silence.py interview.m4a -n dynaudnorm
```

The normalization is applied first, then silence trimming happens on the normalized audio. This two-step process produces better results for voice recordings.

### Loudness Statistics (loudnorm only)

When using `loudnorm`, detailed loudness measurements are included in the JSON output:

- **input_i**: Input Integrated Loudness (LUFS) - the original loudness level
- **input_tp**: Input True Peak (dBTP) - the highest peak in the original
- **input_lra**: Input Loudness Range (LU) - dynamic range of the original
- **output_i**: Output Integrated Loudness (LUFS) - the normalized loudness level (target: **-16 LUFS**)
- **output_tp**: Output True Peak (dBTP) - the highest peak after normalization (target: -1.5 dBTP)
- **output_lra**: Output Loudness Range (LU) - dynamic range after normalization
- **target_offset**: How much gain was applied (in LU - Loudness Units)

**Loudness Targets:**

- **-16 LUFS**: Optimized for YouTube, Spotify, and streaming platforms (~7 dB louder than broadcast standard)
- **-1.5 dBTP**: True peak limit to prevent clipping
- **11 LU**: Target loudness range for consistent dynamics

**Platform Comparison:**

- YouTube target: -14 LUFS (our -16 LUFS is very close)
- Spotify target: -14 LUFS
- Broadcast TV: -24 LUFS (much quieter)

These measurements help you understand exactly what the normalization did to your audio and ensure it's competitive with other online content.

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

### Standard Output

```text
Processing: video.mp4
  ✓ MP3 saved to: trimmed_output/video_trimmed.mp3
  ✓ WAV saved to: trimmed_output/video_trimmed.wav
  ✓ Original: 120.5s → Trimmed: 95.3s
  ✓ Removed 25.2s of silence (20.9%)
```

### JSON Output (`--json`)

When using `--json`, all output is formatted as JSON to STDOUT for easy parsing by other utilities:

**Single file:**

```json
{
  "input_file": "video.mp4",
  "success": true,
  "error": null,
  "output_files": {
    "mp3": "trimmed_output/video_trimmed.mp3",
    "lossless": "trimmed_output/video_trimmed.wav",
    "lossless_format": "wav"
  },
  "stats": {
    "original_duration_seconds": 120.5,
    "trimmed_duration_seconds": 95.3,
    "time_saved_seconds": 25.2,
    "percent_saved": 20.9,
    "normalization": "loudnorm",
    "loudness": {
      "input_i": "-26.5",
      "input_tp": "-4.8",
      "input_lra": "5.3",
      "output_i": "-24.7",
      "output_tp": "-4.3",
      "output_lra": "3.9",
      "target_offset": "+0.7"
    }
  }
}
```

**Directory batch processing:**

```json
{
  "input_directory": "./videos",
  "success": true,
  "error": null,
  "files": [
    {
      "input_file": "video1.mp4",
      "success": true,
      "error": null,
      "output_files": { "mp3": "...", "lossless": "..." },
      "stats": { "original_duration_seconds": 120.5, ... }
    },
    {
      "input_file": "video2.mp4",
      "success": true,
      "error": null,
      "output_files": { "mp3": "...", "lossless": "..." },
      "stats": { "original_duration_seconds": 85.2, ... }
    }
  ],
  "summary": {
    "total_files": 2,
    "successful": 2,
    "failed": 0
  }
}
```

## How It Works

This tool is a simple Python wrapper around ffmpeg's built-in silence detection and removal capabilities. All the heavy lifting is done by ffmpeg itself.

### Safe Mode (Default)
Uses ffmpeg's `silenceremove` filter to trim silence from start and end only.

### Aggressive Mode
Uses a multi-step ffmpeg approach:

1. **Detect**: Uses ffmpeg's `silencedetect` filter to find all silence periods
2. **Extract**: Cuts out non-silent segments with `-c copy` (fast!)
3. **Concatenate**: Joins segments back together using ffmpeg's concat demuxer
4. **Export**: Outputs as MP3 and lossless WAV/AIFF

## License

Free to use and modify for any purpose.
