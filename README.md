# Vernacia

Automated system to process native language videos into learning materials with accurate subtitles and perfect timing splits.

## Installation & Setup

### Prerequisites
- Python 3.7+
- OpenAI API key ([get one here](https://platform.openai.com/api-keys))

### 1. Clone Repository
```bash
git clone https://github.com/vigil-313/vernacia.git
cd vernacia
```

### 2. Install System Dependencies
```bash
# macOS
brew install yt-dlp ffmpeg

# Linux (Ubuntu/Debian)
sudo apt update && sudo apt install yt-dlp ffmpeg

# Linux (other distros) - install yt-dlp via pip if not available
pip install yt-dlp
```

### 3. Setup Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

### 4. Configure API Key
```bash
# Set your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'

# Or add to ~/.bashrc or ~/.zshrc for persistence:
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
```

## Quick Start

### 1. Add Videos to Processing Queue

#### Basic Adding
```bash
# Add entire YouTube playlist
python scripts/add_videos.py --playlist "series_name" --title "Series Title" --url "https://youtube.com/playlist?list=..."

# Add single video
python scripts/add_videos.py --playlist "series_name" --video "https://youtube.com/watch?v=..."

# Check current status
python scripts/add_videos.py --status --playlist dummy
```

#### Configure Split Count
```bash
# Add playlist with 1 split per video (good for short comedy clips)
python scripts/add_videos.py --playlist "comedy_shorts" --url "https://youtube.com/playlist?list=..." --splits 1

# Add playlist with 5 splits per video (good for very long content)
python scripts/add_videos.py --playlist "long_lectures" --url "https://youtube.com/playlist?list=..." --splits 5

# Default is 3 splits if not specified
python scripts/add_videos.py --playlist "audiobooks" --url "https://youtube.com/playlist?list=..."

# Works with single videos too
python scripts/add_videos.py --playlist "test" --video "https://youtube.com/watch?v=..." --splits 2
```

### 2. Process Videos

#### Basic Processing
```bash
# Process next 2 videos (recommended for testing)
python scripts/main.py 2

# Process all pending videos
python scripts/main.py

# Process with custom retry attempts
python scripts/main.py 2 --retries 5
```

#### Target Specific Playlists
```bash
# Process 3 videos from specific playlist
python scripts/main.py 3 --playlist zhushanlang

# Process all videos from specific playlist
python scripts/main.py --playlist zhushanlang

# List available playlists (will show error + playlist names if you use wrong name)
python scripts/main.py 1 --playlist invalid_name
```

#### Video Quality Options
```bash
# High quality video (up to 1080p) - good for visual content like comedy shorts
python scripts/main.py 1 --playlist zhushanlang --hq-video

# Low quality video (480p, default) - good for audiobooks to save space
python scripts/main.py 2 --playlist ghost_blows_light

# Combine all options
python scripts/main.py 5 --playlist zhushanlang --hq-video --retries 3
```

#### Resume Processing
The script automatically resumes where you left off:
```bash
# Continue processing where you left off
python scripts/main.py 2
```

## Features

- ✅ **Smart Video Processing**: Downloads optimized formats to avoid YouTube blocks
- ✅ **Accurate Chinese Subtitles**: OpenAI Whisper API with optimized audio quality  
- ✅ **Intelligent Splitting**: Sentence-aware splits with 15s overlap for smooth learning
- ✅ **Perfect Sync**: Maintains precise timing between video and subtitle parts
- ✅ **Playlist Targeting**: Process specific playlists instead of all videos
- ✅ **Video Quality Options**: Choose high quality (1080p) or low quality (480p) downloads
- ✅ **Retry Logic**: Exponential backoff handles YouTube rate limiting
- ✅ **Resume Capability**: Automatic cleanup and continuation of interrupted downloads
- ✅ **Error Recovery**: Detailed error tracking with configurable retry attempts
- ✅ **Organized Output**: Structured by playlist with manifest tracking
- ✅ **Environment Management**: Easy setup with .env file support
- ✅ **Filename Safety**: Video ID prefixes prevent file confusion bugs
- ✅ **Configurable Splits**: Set split count when adding videos (1-5+ splits per video)

## Directory Structure

```
vernacia/
├── manifest.json           # Master processing queue (git ignored)
├── scripts/
│   ├── main.py            # Main processing script
│   └── add_videos.py      # Utility to add videos/playlists
├── playlists/
│   ├── ghost_blows_light/ # Example audiobook playlist
│   │   ├── videos/        # Raw downloaded videos (with video ID prefixes)
│   │   └── processed/     # Split videos + SRT files
│   └── zhushanlang/       # Example comedy shorts playlist
│       ├── videos/        # Raw downloaded videos
│       └── processed/     # Split videos + SRT files
└── README.md
```

## Manifest Format

The `manifest.json` file controls what gets processed:

```json
{
  "playlists": {
    "playlist_name": {
      "title": "Display Name",
      "url": "https://youtube.com/playlist?list=...",
      "videos": [
        {
          "url": "https://youtube.com/watch?v=...",
          "title": "Video Title",
          "splits": 3,           // Optional: override default splits
          "status": "pending",   // pending/processing/completed/failed
          "error": null,
          "processed_files": []
        }
      ]
    }
  }
}
```

## Video Status

- **pending**: Ready to process
- **processing**: Currently being processed
- **completed**: Successfully processed
- **failed**: Error occurred (see error field)

## Output Files

For each video, you get sentence-aware splits with 15-second overlap:
- `videoID_video_name_part1.mp4` + `videoID_video_name_part1.srt` (00:00 → ~33% + overlap)
- `videoID_video_name_part2.mp4` + `videoID_video_name_part2.srt` (33% - overlap → 66% + overlap)  
- `videoID_video_name_part3.mp4` + `videoID_video_name_part3.srt` (66% - overlap → end)

**Perfect for Language Reactor's Video File tool!**
- Smart splits at sentence boundaries (no mid-sentence cuts)
- Overlapping content provides context between parts
- Video ID prefix prevents filename conflicts
- Configurable video quality (480p default, 1080p with --hq-video)

## Cost Estimation

OpenAI Whisper API: ~$0.006 per minute of audio
- 1 hour video ≈ $0.36
- 3 hour video ≈ $1.08

## Troubleshooting

**"OPENAI_API_KEY not set"**
- Get API key from: https://platform.openai.com/api-keys
- Run: `export OPENAI_API_KEY='your-key'` or add to .env file

**Video download fails**
- Check if video is available/public
- Try updating yt-dlp: `yt-dlp -U`
- Check YouTube Premium cookies (script uses Chrome cookies)

**Audio too large errors**
- Script automatically splits large audio files
- Check your internet connection

**Wrong playlist name**
- Script shows available playlists if you use invalid name
- Check manifest.json for exact playlist IDs

**Resume processing**
- Just run `python scripts/main.py` again
- It will skip completed videos and continue with pending ones
- Use `--playlist` to target specific playlist

**File conflicts/confusion**
- Fixed with video ID prefixes (videoID_filename.mp4)
- Old files may need manual cleanup

## Dependencies

- Python 3.7+
- yt-dlp (video downloading)
- ffmpeg (audio/video processing)
- OpenAI Python package
- Active internet connection
- OpenAI API key with credits