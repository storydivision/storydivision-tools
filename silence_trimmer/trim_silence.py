#!/usr/bin/env python3
"""
Trim silence from video/audio files and save as MP3.
Supports MP4 and MP3 input files.
"""

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple


def check_ffmpeg():
    """Check if ffmpeg is installed."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: ffmpeg is not installed or not in PATH")
        print("Install it with:")
        print("  - macOS: brew install ffmpeg")
        print("  - Linux: sudo apt install ffmpeg (Ubuntu/Debian) or sudo dnf install ffmpeg (Fedora)")
        sys.exit(1)


def get_audio_duration(file_path: Path) -> float:
    """Get duration of audio/video file in seconds."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError) as e:
        print(f"Warning: Could not get duration for {file_path}: {e}")
        return 0.0


def detect_silences(
    input_file: Path,
    silence_threshold: int,
    min_silence_duration: float,
    verbose: bool = False
) -> List[Tuple[float, float]]:
    """
    Detect silence periods in audio using FFmpeg silencedetect filter.
    
    Returns:
        List of (start_time, end_time) tuples for each silence period
    """
    cmd = [
        "ffmpeg",
        "-i", str(input_file),
        "-af", f"silencedetect=noise={silence_threshold}dB:d={min_silence_duration}",
        "-f", "null",
        "-"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=True
        )
        output = result.stdout
    except subprocess.CalledProcessError as e:
        output = e.stdout if e.stdout else ""
    
    if verbose:
        print("Silence detection output:")
        print(output)
    
    # Parse silence periods from output
    # Example: [silencedetect @ 0x...] silence_start: 1.307
    #          [silencedetect @ 0x...] silence_end: 1.668 | silence_duration: 0.360
    silences = []
    silence_start_pattern = re.compile(r'silence_start: ([\d.]+)')
    silence_end_pattern = re.compile(r'silence_end: ([\d.]+)')
    
    current_start = None
    for line in output.split('\n'):
        start_match = silence_start_pattern.search(line)
        if start_match:
            current_start = float(start_match.group(1))
        
        end_match = silence_end_pattern.search(line)
        if end_match and current_start is not None:
            silence_end = float(end_match.group(1))
            silences.append((current_start, silence_end))
            current_start = None
    
    return silences


def remove_silences_ffmpeg(
    input_file: Path,
    output_file: Path,
    silence_threshold: int,
    min_silence_duration: float,
    padding: float,
    bitrate: str,
    verbose: bool,
    lossless_format: Optional[str]
) -> bool:
    """
    Remove silences using FFmpeg multi-command approach.
    
    Process:
    1. Detect all silences
    2. Calculate non-silent segments (with padding)
    3. Extract each segment
    4. Concatenate segments
    """
    # Step 1: Detect silences
    if verbose:
        print(f"Detecting silences (threshold: {silence_threshold}dB, min duration: {min_silence_duration}s)...")
    
    silences = detect_silences(input_file, silence_threshold, min_silence_duration, verbose)
    
    if not silences:
        if verbose:
            print("No silences detected. Copying input to output.")
        # No silences, just copy the file
        subprocess.run([
            "ffmpeg", "-i", str(input_file),
            "-b:a", bitrate, "-y", str(output_file)
        ], check=True, capture_output=not verbose)
        if lossless_format:
            lossless_file = output_file.with_suffix(f".{lossless_format}")
            subprocess.run([
                "ffmpeg", "-i", str(input_file),
                "-y", str(lossless_file)
            ], check=True, capture_output=not verbose)
        return True
    
    if verbose:
        print(f"Found {len(silences)} silence periods")
        for i, (start, end) in enumerate(silences, 1):
            print(f"  Silence {i}: {start:.3f}s - {end:.3f}s (duration: {end-start:.3f}s)")
    
    # Step 2: Calculate non-silent segments (no padding for now)
    # Strategy: Keep all audio EXCEPT the detected silences
    total_duration = get_audio_duration(input_file)
    segments = []
    current_pos = 0.0
    
    for silence_start, silence_end in silences:
        # Add non-silent audio from current position to start of this silence
        if silence_start > current_pos:
            segments.append((current_pos, silence_start))
        
        # Skip the silence entirely
        current_pos = silence_end
    
    # Add remaining audio after last silence
    if current_pos < total_duration:
        segments.append((current_pos, total_duration))
    
    if not segments:
        print("Warning: No segments to keep after silence removal")
        return False
    
    if verbose:
        print(f"\nKeeping {len(segments)} segments:")
        for i, (start, end) in enumerate(segments, 1):
            print(f"  Segment {i}: {start:.3f}s - {end:.3f}s (duration: {end-start:.3f}s)")
    
    # Step 3 & 4: Extract segments and concatenate
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        segment_files = []
        
        # Extract each segment
        for i, (start, end) in enumerate(segments):
            segment_file = temp_path / f"segment_{i:04d}.mp4"
            segment_files.append(segment_file)
            
            # Always use -c copy for fast extraction
            # FFmpeg concat filter handles small segments fine
            cmd = [
                "ffmpeg", "-i", str(input_file),
                "-ss", str(start), "-to", str(end),
                "-c", "copy",
                "-y", str(segment_file)
            ]
            
            subprocess.run(cmd, check=True, capture_output=not verbose)
        
        # Create concat file list
        concat_file = temp_path / "concat_list.txt"
        with open(concat_file, 'w') as f:
            for segment_file in segment_files:
                f.write(f"file '{segment_file}'\n")
        
        # Concatenate segments to MP3
        concat_cmd = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-b:a", bitrate,
            "-y", str(output_file)
        ]
        subprocess.run(concat_cmd, check=True, capture_output=not verbose)
        
        # Create lossless version if requested
        if lossless_format:
            lossless_file = output_file.with_suffix(f".{lossless_format}")
            lossless_cmd = [
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-y", str(lossless_file)
            ]
            subprocess.run(lossless_cmd, check=True, capture_output=not verbose)
    
    return True


def trim_silence(
    input_file: Path,
    output_file: Path,
    silence_threshold: int = -30,
    min_silence_duration: float = 0.2,
    padding: float = 0.1,
    bitrate: str = "128k",
    verbose: bool = False,
    aggressive: bool = False,
    lossless_format: Optional[str] = "wav"
) -> bool:
    """
    Trim silence from audio/video file and save as MP3.
    
    Args:
        input_file: Path to input file (MP4 or MP3)
        output_file: Path to output MP3 file
        silence_threshold: Volume level considered silence in dB (e.g., -40)
        min_silence_duration: Minimum duration of silence to remove in seconds
        padding: Amount of silence to keep around speech in seconds
        bitrate: Output MP3 bitrate (e.g., "128k", "192k")
        verbose: Print ffmpeg output
        aggressive: If True, remove silence throughout. If False, only trim start/end
        lossless_format: Format for lossless output ("wav", "aiff", or None to skip)
        
    Returns:
        True if successful, False otherwise
    """
    # Build ffmpeg command with silenceremove filter
    # Default: only remove silence from start and end (stop_periods=1)
    # Aggressive: remove silence throughout (stop_periods=-1)
    
    if aggressive:
        # Use FFmpeg multi-command approach to remove silences
        # This detects silences, extracts non-silent segments, and concatenates them
        return remove_silences_ffmpeg(
            input_file,
            output_file,
            silence_threshold,
            min_silence_duration,
            padding,
            bitrate,
            verbose,
            lossless_format
        )
    else:
        # Only trim silence from start and end using areverse trick
        # Use a less strict threshold for end trimming to catch background noise/rustling
        # This is more reliable than stop_periods=1
        end_threshold = max(silence_threshold, -35)  # At least -35dB for end (catches more noise)
        
        audio_filter = (
            f"silenceremove="
            f"start_periods=1:"
            f"start_threshold={silence_threshold}dB:"
            f"start_silence={padding},"
            f"areverse,"
            f"silenceremove="
            f"start_periods=1:"
            f"start_threshold={end_threshold}dB:"  # Less strict for end
            f"start_silence={padding},"
            f"areverse"
        )
    
    cmd = [
        "ffmpeg",
        "-i", str(input_file),
        "-af", audio_filter,
        "-b:a", bitrate,
        "-y",  # Overwrite output file
        str(output_file)
    ]
    
    try:
        # Process MP3
        if verbose:
            print(f"Running: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)
        else:
            subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True
            )
        
        # Also create lossless version if requested
        if lossless_format:
            lossless_file = output_file.with_suffix(f".{lossless_format}")
            lossless_cmd = [
                "ffmpeg",
                "-i", str(input_file),
                "-af", audio_filter,
                "-y",
                str(lossless_file)
            ]
            if verbose:
                print(f"Creating lossless: {' '.join(lossless_cmd)}")
                subprocess.run(lossless_cmd, check=True)
            else:
                subprocess.run(
                    lossless_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=True
                )
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: {e}")
        if verbose and e.stderr:
            print(e.stderr.decode())
        return False


def process_file(
    input_file: Path,
    output_dir: Optional[Path] = None,
    **kwargs
) -> bool:
    """Process a single file."""
    if not input_file.exists():
        print(f"Error: File not found: {input_file}")
        return False
    
    if input_file.suffix.lower() not in ['.mp4', '.mp3']:
        print(f"Skipping {input_file}: Not an MP4 or MP3 file")
        return False
    
    # Determine output directory
    if output_dir is None:
        output_dir = input_file.parent / "trimmed_output"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output filename
    output_file = output_dir / f"{input_file.stem}_trimmed.mp3"
    
    print(f"Processing: {input_file.name}")
    
    # Get original duration
    original_duration = get_audio_duration(input_file)
    
    # Process the file
    success = trim_silence(input_file, output_file, **kwargs)
    
    if success:
        # Get new duration
        new_duration = get_audio_duration(output_file)
        
        if original_duration > 0:
            time_saved = original_duration - new_duration
            percent_saved = (time_saved / original_duration) * 100
            print(f"  ✓ MP3 saved to: {output_file}")
            
            # Show lossless file if created
            lossless_format = kwargs.get('lossless_format')
            if lossless_format:
                lossless_file = output_dir / f"{input_file.stem}_trimmed.{lossless_format}"
                print(f"  ✓ {lossless_format.upper()} saved to: {lossless_file}")
            
            print(f"  ✓ Original: {original_duration:.1f}s → Trimmed: {new_duration:.1f}s")
            print(f"  ✓ Removed {time_saved:.1f}s of silence ({percent_saved:.1f}%)")
        else:
            print(f"  ✓ Saved to: {output_file}")
    
    return success


def process_directory(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    **kwargs
) -> tuple[int, int]:
    """
    Process all MP4 and MP3 files in a directory.
    
    Returns:
        Tuple of (successful_count, total_count)
    """
    if not input_dir.is_dir():
        print(f"Error: Not a directory: {input_dir}")
        return 0, 0
    
    # Find all MP4 and MP3 files
    files = list(input_dir.glob("*.mp4")) + list(input_dir.glob("*.mp3"))
    files += list(input_dir.glob("*.MP4")) + list(input_dir.glob("*.MP3"))
    
    if not files:
        print(f"No MP4 or MP3 files found in {input_dir}")
        return 0, 0
    
    print(f"Found {len(files)} file(s) to process\n")
    
    successful = 0
    for i, file in enumerate(files, 1):
        print(f"[{i}/{len(files)}]", end=" ")
        if process_file(file, output_dir, **kwargs):
            successful += 1
        print()  # Empty line between files
    
    return successful, len(files)


def main():
    parser = argparse.ArgumentParser(
        description="Trim silence from video/audio files and save as MP3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single file with defaults
  %(prog)s video.mp4
  
  # Process with custom silence threshold
  %(prog)s video.mp4 -t -35
  
  # Process all files in a directory
  %(prog)s -d ./videos
  
  # Custom settings for aggressive silence removal
  %(prog)s video.mp4 -t -50 -m 0.1 -p 0.05
  
  # High quality output
  %(prog)s video.mp4 -b 320k
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "input_file",
        nargs="?",
        type=Path,
        help="Input file (MP4 or MP3)"
    )
    input_group.add_argument(
        "-d", "--directory",
        type=Path,
        help="Process all MP4/MP3 files in directory"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output directory (default: creates 'trimmed_output' folder in source location)"
    )
    
    # Silence detection options
    parser.add_argument(
        "-t", "--threshold",
        type=int,
        default=-30,
        help="Silence threshold in dB (default: -30). Lower = stricter. Try -30 to -50"
    )
    parser.add_argument(
        "-m", "--min-duration",
        type=float,
        default=0.2,
        help="Minimum silence duration to remove in seconds (default: 0.2)"
    )
    parser.add_argument(
        "-p", "--padding",
        type=float,
        default=0.1,
        help="Padding to keep around speech in seconds (default: 0.1)"
    )
    
    # Quality options
    parser.add_argument(
        "-b", "--bitrate",
        default="128k",
        help="Output MP3 bitrate (default: 128k). Options: 128k, 192k, 320k"
    )
    
    # Lossless output options
    parser.add_argument(
        "--lossless",
        choices=["wav", "aiff", "none"],
        default="wav",
        help="Lossless format to create alongside MP3 (default: wav). Use 'none' to skip"
    )
    
    # Other options
    parser.add_argument(
        "-a", "--aggressive",
        action="store_true",
        help="Remove silence throughout audio (default: only trim start/end). WARNING: May cut speech!"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed ffmpeg output"
    )
    
    args = parser.parse_args()
    
    # Check ffmpeg installation
    check_ffmpeg()
    
    # Prepare kwargs for processing functions
    lossless_format = None if args.lossless == "none" else args.lossless
    
    process_kwargs = {
        "silence_threshold": args.threshold,
        "min_silence_duration": args.min_duration,
        "padding": args.padding,
        "bitrate": args.bitrate,
        "verbose": args.verbose,
        "aggressive": args.aggressive,
        "lossless_format": lossless_format,
    }
    
    # Process based on input type
    if args.directory:
        successful, total = process_directory(
            args.directory,
            args.output,
            **process_kwargs
        )
        print(f"\nCompleted: {successful}/{total} files processed successfully")
        sys.exit(0 if successful == total else 1)
    else:
        success = process_file(
            args.input_file,
            args.output,
            **process_kwargs
        )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
