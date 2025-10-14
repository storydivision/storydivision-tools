#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# dependencies = []
# ///
"""
Trim silence from video/audio files and save as MP3.
Supports common audio and video formats that ffmpeg can process.
"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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


def parse_loudnorm_stats(stderr_output: str) -> Optional[Dict]:
    """
    Parse loudness normalization statistics from ffmpeg stderr output.
    
    Args:
        stderr_output: The stderr output from ffmpeg with loudnorm filter
        
    Returns:
        Dictionary with loudness statistics or None if parsing fails
    """
    try:
        stats = {}
        lines = stderr_output.split('\n')
        
        for line in lines:
            line = line.strip()
            if 'Input Integrated:' in line:
                stats['input_i'] = line.split(':')[1].strip().replace(' LUFS', '')
            elif 'Input True Peak:' in line:
                stats['input_tp'] = line.split(':')[1].strip().replace(' dBTP', '')
            elif 'Input LRA:' in line:
                stats['input_lra'] = line.split(':')[1].strip().replace(' LU', '')
            elif 'Output Integrated:' in line:
                stats['output_i'] = line.split(':')[1].strip().replace(' LUFS', '')
            elif 'Output True Peak:' in line:
                stats['output_tp'] = line.split(':')[1].strip().replace(' dBTP', '')
            elif 'Output LRA:' in line:
                stats['output_lra'] = line.split(':')[1].strip().replace(' LU', '')
            elif 'Target Offset:' in line:
                stats['target_offset'] = line.split(':')[1].strip().replace(' LU', '')
        
        # Only return if we got at least some stats
        return stats if stats else None
    except Exception:
        return None


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
) -> Tuple[bool, Optional[Dict]]:
    """
    Remove silences using FFmpeg multi-command approach.
    
    Process:
    1. Detect all silences
    2. Calculate non-silent segments (with padding)
    3. Extract each segment
    4. Concatenate segments
    
    Returns:
        Tuple of (success: bool, loudness_stats: Optional[Dict])
        Note: Aggressive mode doesn't support loudness stats
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
        return True, None
    
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
        return False, None
    
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
    
    return True, None


def trim_silence(
    input_file: Path,
    output_file: Path,
    silence_threshold: int = -30,
    min_silence_duration: float = 0.2,
    padding: float = 0.2,
    bitrate: str = "128k",
    verbose: bool = False,
    aggressive: bool = False,
    lossless_format: Optional[str] = "wav",
    normalize: Optional[str] = None
) -> Tuple[bool, Optional[Dict]]:
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
        normalize: Normalization method ("loudnorm", "dynaudnorm", or None to skip)
        
    Returns:
        Tuple of (success: bool, loudness_stats: Optional[Dict])
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
        # Use a LESS strict threshold for end trimming to avoid cutting off word endings
        # This is more reliable than stop_periods=1
        end_threshold = min(silence_threshold, -35)  # At most -35dB for end (less aggressive)
        
        # Build audio filter chain
        filters = []
        
        # Add normalization if requested (applied FIRST)
        loudness_stats = None
        if normalize:
            if normalize == "loudnorm":
                # EBU R128 loudness normalization (industry standard for broadcast/streaming)
                # Use print_format=summary to get loudness measurements
                filters.append("loudnorm=print_format=summary")
            elif normalize == "dynaudnorm":
                # Dynamic audio normalizer (faster, simpler)
                filters.append("dynaudnorm")
            else:
                # Invalid normalize value, skip
                pass
        
        # Add silence removal filters
        silence_filter = (
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
        filters.append(silence_filter)
        
        # Join filters with comma
        audio_filter = ",".join(filters)
    
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
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        else:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
                text=True
            )
        
        # Parse loudness stats if using loudnorm
        if normalize == "loudnorm":
            loudness_stats = parse_loudnorm_stats(result.stderr)
        
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
        
        return True, loudness_stats
    except subprocess.CalledProcessError as e:
        print(f"Error processing {input_file}: {e}")
        if verbose and e.stderr:
            print(e.stderr if isinstance(e.stderr, str) else e.stderr.decode())
        return False, None


def process_file(
    input_file: Path,
    output_dir: Optional[Path] = None,
    json_mode: bool = False,
    **kwargs
) -> Dict:
    """Process a single file.
    
    Returns:
        Dictionary with processing results (for JSON mode) or success status
    """
    result = {
        "input_file": str(input_file),
        "success": False,
        "error": None,
        "output_files": {},
        "stats": {}
    }
    
    if not input_file.exists():
        error_msg = f"File not found: {input_file}"
        if not json_mode:
            print(f"Error: {error_msg}")
        result["error"] = error_msg
        return result
    
    # Common audio and video formats supported by ffmpeg
    supported_extensions = {
        # Video formats
        '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg',
        '.3gp', '.ogv', '.ts', '.mts', '.m2ts', '.vob', '.asf', '.rm', '.rmvb', '.divx',
        # Audio formats
        '.mp3', '.m4a', '.aac', '.wav', '.flac', '.ogg', '.opus', '.wma', '.aiff', '.ape',
        '.ac3', '.dts', '.alac', '.amr', '.au', '.caf', '.mka', '.oga', '.ra', '.wv',
        '.tta', '.tak', '.mpc', '.dsf', '.dff'
    }
    
    if input_file.suffix.lower() not in supported_extensions:
        error_msg = f"Unsupported file format: {input_file.suffix}"
        if not json_mode:
            print(f"Skipping {input_file}: {error_msg}")
        result["error"] = error_msg
        return result
    
    # Determine output directory
    if output_dir is None:
        output_dir = input_file.parent / "trimmed_output"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output filename
    output_file = output_dir / f"{input_file.stem}_trimmed.mp3"
    
    if not json_mode:
        print(f"Processing: {input_file.name}")
    
    # Get original duration
    original_duration = get_audio_duration(input_file)
    
    # Process the file
    success, loudness_stats = trim_silence(input_file, output_file, **kwargs)
    
    if success:
        # Get new duration
        new_duration = get_audio_duration(output_file)
        
        result["success"] = True
        result["output_files"]["mp3"] = str(output_file)
        
        if original_duration > 0:
            time_saved = original_duration - new_duration
            percent_saved = (time_saved / original_duration) * 100
            
            result["stats"] = {
                "original_duration_seconds": round(original_duration, 2),
                "trimmed_duration_seconds": round(new_duration, 2),
                "time_saved_seconds": round(time_saved, 2),
                "percent_saved": round(percent_saved, 2),
                "normalization": kwargs.get('normalize') if kwargs.get('normalize') else None
            }
            
            # Add loudness stats if available
            if loudness_stats:
                result["stats"]["loudness"] = loudness_stats
            
            if not json_mode:
                print(f"  ✓ MP3 saved to: {output_file}")
            
            # Show lossless file if created
            lossless_format = kwargs.get('lossless_format')
            if lossless_format:
                lossless_file = output_dir / f"{input_file.stem}_trimmed.{lossless_format}"
                result["output_files"]["lossless"] = str(lossless_file)
                result["output_files"]["lossless_format"] = lossless_format
                if not json_mode:
                    print(f"  ✓ {lossless_format.upper()} saved to: {lossless_file}")
            
            if not json_mode:
                print(f"  ✓ Original: {original_duration:.1f}s → Trimmed: {new_duration:.1f}s")
                print(f"  ✓ Removed {time_saved:.1f}s of silence ({percent_saved:.1f}%)")
        else:
            if not json_mode:
                print(f"  ✓ Saved to: {output_file}")
    else:
        result["error"] = "Processing failed"
    
    return result


def process_directory(
    input_dir: Path,
    output_dir: Optional[Path] = None,
    json_mode: bool = False,
    **kwargs
) -> Dict:
    """
    Process all MP4 and MP3 files in a directory.
    
    Returns:
        Dictionary with processing results for all files
    """
    result = {
        "input_directory": str(input_dir),
        "success": False,
        "error": None,
        "files": [],
        "summary": {
            "total_files": 0,
            "successful": 0,
            "failed": 0
        }
    }
    
    if not input_dir.is_dir():
        error_msg = f"Not a directory: {input_dir}"
        if not json_mode:
            print(f"Error: {error_msg}")
        result["error"] = error_msg
        return result
    
    # Find all supported audio and video files
    supported_patterns = [
        # Video formats
        '*.mp4', '*.mkv', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm', '*.m4v',
        '*.mpg', '*.mpeg', '*.3gp', '*.ogv', '*.ts', '*.mts', '*.m2ts', '*.vob',
        '*.asf', '*.rm', '*.rmvb', '*.divx',
        # Audio formats
        '*.mp3', '*.m4a', '*.aac', '*.wav', '*.flac', '*.ogg', '*.opus', '*.wma',
        '*.aiff', '*.ape', '*.ac3', '*.dts', '*.alac', '*.amr', '*.au', '*.caf',
        '*.mka', '*.oga', '*.ra', '*.wv', '*.tta', '*.tak', '*.mpc', '*.dsf', '*.dff'
    ]
    
    files = []
    for pattern in supported_patterns:
        files.extend(input_dir.glob(pattern))
        files.extend(input_dir.glob(pattern.upper()))
    
    if not files:
        error_msg = f"No supported audio/video files found in {input_dir}"
        if not json_mode:
            print(error_msg)
        result["error"] = error_msg
        return result
    
    if not json_mode:
        print(f"Found {len(files)} file(s) to process\n")
    
    result["summary"]["total_files"] = len(files)
    
    for i, file in enumerate(files, 1):
        if not json_mode:
            print(f"[{i}/{len(files)}]", end=" ")
        
        file_result = process_file(file, output_dir, json_mode=json_mode, **kwargs)
        result["files"].append(file_result)
        
        if file_result["success"]:
            result["summary"]["successful"] += 1
        else:
            result["summary"]["failed"] += 1
        
        if not json_mode:
            print()  # Empty line between files
    
    result["success"] = result["summary"]["failed"] == 0
    return result


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
        help="Input audio or video file (supports most common formats: MP4, MKV, AVI, MOV, MP3, M4A, FLAC, WAV, etc.)"
    )
    input_group.add_argument(
        "-d", "--directory",
        type=Path,
        help="Process all supported audio/video files in directory"
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
        default=0.2,
        help="Padding to keep around speech in seconds (default: 0.2)"
    )
    
    # Quality options
    parser.add_argument(
        "-b", "--bitrate",
        default="128k",
        help="Output MP3 bitrate (default: 128k). Options: 128k, 192k, 320k"
    )
    
    # Lossless output options
    parser.add_argument(
        "-l", "--lossless",
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
        "-n", "--normalize",
        type=str,
        nargs="?",
        const="loudnorm",
        default=None,
        choices=["loudnorm", "dynaudnorm"],
        metavar="METHOD",
        help="Apply audio normalization before silence detection. "
             "Options: loudnorm (default, EBU R128 standard for broadcast/streaming), "
             "dynaudnorm (faster, dynamic normalization). "
             "Use -n alone for loudnorm, or -n dynaudnorm for dynamic. "
             "Recommended for speech/voice content."
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed ffmpeg output"
    )
    parser.add_argument(
        "-j", "--json",
        action="store_true",
        help="Output results as JSON to STDOUT (suppresses all other output)"
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
        "normalize": args.normalize,
    }
    
    # Process based on input type
    if args.directory:
        result = process_directory(
            args.directory,
            args.output,
            json_mode=args.json,
            **process_kwargs
        )
        
        if args.json:
            print(json.dumps(result, indent=2))
            sys.exit(0 if result["success"] else 1)
        else:
            print(f"\nCompleted: {result['summary']['successful']}/{result['summary']['total_files']} files processed successfully")
            sys.exit(0 if result["success"] else 1)
    else:
        result = process_file(
            args.input_file,
            args.output,
            json_mode=args.json,
            **process_kwargs
        )
        
        if args.json:
            print(json.dumps(result, indent=2))
        
        sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
