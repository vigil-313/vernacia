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
```bash
# Add entire YouTube playlist
python scripts/add_videos.py --playlist "series_name" --title "Series Title" --url "https://youtube.com/playlist?list=..."

# Add single video
python scripts/add_videos.py --playlist "series_name" --video "https://youtube.com/watch?v=..."

# Check current status
python scripts/add_videos.py --status --playlist dummy
```

### 2. Process Videos
```bash
# Process next 2 videos (recommended for testing)
python scripts/main.py 2

# Process with custom retry attempts
python scripts/main.py 1 --retries 5

# Process all pending videos
python scripts/main.py

# Continue processing where you left off (resumes automatically)
python scripts/main.py 2
```

## Features

- ✅ **Smart Video Processing**: Downloads optimized formats to avoid YouTube blocks
- ✅ **Accurate Chinese Subtitles**: OpenAI Whisper API with optimized audio quality
- ✅ **Intelligent Splitting**: Sentence-aware splits with 15s overlap for smooth learning
- ✅ **Perfect Sync**: Maintains precise timing between video and subtitle parts
- ✅ **Retry Logic**: Exponential backoff handles YouTube rate limiting
- ✅ **Resume Capability**: Automatic cleanup and continuation of interrupted downloads
- ✅ **Error Recovery**: Detailed error tracking with configurable retry attempts
- ✅ **Organized Output**: Structured by playlist with manifest tracking
- ✅ **Environment Management**: Easy setup with .env file support

## Directory Structure

```
vernacia/
├── manifest.json           # Master processing queue
├── scripts/
│   └── main.py            # Main processing script
├── playlists/
│   └── ghost_blows_light/ # Example playlist
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
- `video_name_part1.mp4` + `video_name_part1.srt` (00:00 → ~33% + overlap)
- `video_name_part2.mp4` + `video_name_part2.srt` (33% - overlap → 66% + overlap)  
- `video_name_part3.mp4` + `video_name_part3.srt` (66% - overlap → end)

**Perfect for Language Reactor's Video File tool!**
- Smart splits at sentence boundaries (no mid-sentence cuts)
- Overlapping content provides context between parts
- High-quality audio in video, optimized transcription speed

## Cost Estimation

OpenAI Whisper API: ~$0.006 per minute of audio
- 1 hour video ≈ $0.36
- 3 hour video ≈ $1.08

## Troubleshooting

**"OPENAI_API_KEY not set"**
- Get API key from: https://platform.openai.com/api-keys
- Run: `export OPENAI_API_KEY='your-key'`

**Video download fails**
- Check if video is available/public
- Try updating yt-dlp: `yt-dlp -U`

**Audio too large errors**
- Script automatically splits large audio files
- Check your internet connection

**Resume processing**
- Just run `python scripts/main.py` again
- It will skip completed videos and continue with pending ones

## Dependencies

- Python 3.7+
- yt-dlp (video downloading)
- ffmpeg (audio/video processing)
- OpenAI Python package
- Active internet connection
- OpenAI API key with credits