# Quick Start Examples

## Single File Processing

```bash
# Basic usage with defaults (Python)
python trim_silence.py videos/S01E02_type_c_parents_no_captions.mp4

# Or with uv (recommended for dependency management)
uv run trim_silence.py videos/S01E02_type_c_parents_no_captions.mp4

# Or make it executable and run
./trim_silence.py videos/S01E02_type_c_parents_no_captions.mp4
```

## Batch Process Directory

```bash
# Process all MP4 and MP3 files in videos folder
python trim_silence.py -d videos
# Or with uv:
uv run trim_silence.py -d videos

# Process with custom output location
python trim_silence.py -d videos -o ./processed_audio
```

## Custom Settings

```bash
# Stricter silence detection (removes more)
python trim_silence.py video.mp4 -t -40

# Lenient silence detection (keeps more audio)
python trim_silence.py video.mp4 -t -25

# Aggressive mode: remove long pauses throughout (>0.6s)
python trim_silence.py video.mp4 --aggressive -m 0.6

# More aggressive: remove pauses >0.4s
python trim_silence.py video.mp4 --aggressive -m 0.4

# High quality output
python trim_silence.py video.mp4 -b 320k

# See what's happening (verbose mode)
python trim_silence.py video.mp4 -v
```

## Real-World Scenarios

### Scenario 1: YouTube Video to Podcast
```bash
# Extract audio from video, remove silence, high quality
python trim_silence.py youtube_video.mp4 -b 192k -t -40
```

### Scenario 2: Clean Up Interview Recording
```bash
# Remove long pauses but keep natural speech rhythm
python trim_silence.py interview.mp3 --aggressive -m 0.7
```

### Scenario 3: Batch Process Course Videos
```bash
# Process all course videos in a folder
python trim_silence.py -d ./course_videos -o ./course_audio -b 128k
```

### Scenario 4: Podcast Editing (Match Premiere Pro)
```bash
# Remove pauses >0.6s like Premiere Pro's "delete pauses" feature
python trim_silence.py lecture.mp4 --aggressive -m 0.6 -b 192k
```

## Understanding the Parameters

### Threshold (`-t`)
- **-30dB**: Very lenient, only removes very quiet sections
- **-40dB**: Default, good for most speech
- **-50dB**: Strict, removes more audio (use carefully)

### Min Duration (`-m`) - Aggressive Mode Only
- **0.4s**: Very aggressive, removes most pauses (use carefully)
- **0.6s**: Recommended default, matches Premiere Pro behavior
- **0.7s**: Conservative, only removes long pauses

### Bitrate (`-b`)
- **128k**: Good quality, smaller files (default)
- **192k**: High quality, balanced size
- **320k**: Maximum quality, larger files

## Troubleshooting

### "Too much audio is being removed!"
```bash
# Use safe mode (only trims start/end)
python trim_silence.py video.mp4

# Or increase min duration in aggressive mode
python trim_silence.py video.mp4 --aggressive -m 0.8
```

### "Not enough silence is removed!"
```bash
# Try aggressive mode with recommended settings
python trim_silence.py video.mp4 --aggressive -m 0.6

# Or use stricter threshold
python trim_silence.py video.mp4 -t -40
```

### "I want to see what ffmpeg is doing"
```bash
# Use verbose mode
python trim_silence.py video.mp4 -v
```

### "ffmpeg not found"
```bash
# Install ffmpeg first
# macOS:
brew install ffmpeg

# Linux (Ubuntu/Debian):
sudo apt install ffmpeg

# Linux (Fedora):
sudo dnf install ffmpeg
```
