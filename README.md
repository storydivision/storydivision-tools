# StoryDivision Tools

A collection of video creation, audio processing, and editing tools designed for content creators.

## 🎯 Project Philosophy

Each tool in this collection is:
- **Self-contained**: Lives in its own subdirectory with dedicated documentation
- **Python-first**: Most tools are written in Python for ease of use and maintenance
- **UV-compatible**: All Python scripts can be run directly via URL using [Astral UV](https://github.com/astral-sh/uv) once published on GitHub
- **Focused**: Does one thing well without unnecessary complexity

## 🛠️ Available Tools

### [silence_trimmer](./silence_trimmer/)
Automatically trim silence from video/audio files and export as MP3. Perfect for cleaning up recordings, podcasts, and video content.

**Quick run with UV:**
```bash
uv run https://raw.githubusercontent.com/storydivision/storydivision-tools/main/silence_trimmer/trim_silence.py --help
```

## 📦 Installation

### Using UV (Recommended)
Each tool can be run directly without installation:
```bash
uv run <tool-directory>/script.py [args]
```

### Traditional Python
Navigate to any tool directory and use standard Python:
```bash
cd <tool-directory>
python script.py [args]
```

## 🚀 Getting Started

1. **Browse tools**: Each subdirectory contains a complete tool with its own README
2. **Check requirements**: Most tools require external dependencies (like ffmpeg)
3. **Run directly**: Use UV for instant execution or clone the repo for local use

## 📋 Tool Structure

Each tool follows this structure:
```
tool-name/
├── README.md           # Tool-specific documentation
├── pyproject.toml      # UV-compatible project metadata
├── script.py           # Main executable script
└── [other files]       # Additional resources as needed
```

## 🤝 Contributing

New tools should:
- Be placed in their own subdirectory
- Include a comprehensive README.md
- Have a pyproject.toml for UV compatibility
- Use `#!/usr/bin/env python3` shebang for direct execution
- Follow the existing tool patterns

## 📝 License

[Add your license here]

## 🔗 Links

- [Astral UV Documentation](https://github.com/astral-sh/uv)
- [GitHub Repository](https://github.com/storydivision/storydivision-tools)
- [Report Issues](https://github.com/storydivision/storydivision-tools/issues)
