#!/usr/bin/env python3
"""
Manifest Helper - Add videos/playlists to processing queue

Usage:
  python scripts/add_videos.py --playlist "playlist_name" --url "https://youtube.com/playlist?list=..."
  python scripts/add_videos.py --playlist "playlist_name" --videos video1.txt video2.txt
  python scripts/add_videos.py --playlist "playlist_name" --video "https://youtube.com/watch?v=..."
"""

import json
import argparse
import subprocess
from pathlib import Path
import sys
import re

class ManifestManager:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.manifest_file = self.base_dir / "manifest.json"
    
    def load_manifest(self):
        """Load or create manifest file"""
        if self.manifest_file.exists():
            with open(self.manifest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return {"playlists": {}}
    
    def save_manifest(self, manifest):
        """Save manifest file"""
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    def get_playlist_videos(self, playlist_url):
        """Extract video URLs from YouTube playlist"""
        cmd = [
            "yt-dlp",
            "--flat-playlist",
            "--print", "url",
            "--print", "title",
            playlist_url
        ]
        
        print(f"📋 Fetching playlist videos from: {playlist_url}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to fetch playlist: {result.stderr}")
        
        lines = result.stdout.strip().split('\n')
        videos = []
        
        # Lines alternate: URL, Title, URL, Title, ...
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                url = lines[i].strip()
                title = lines[i + 1].strip()
                if url.startswith('https://'):
                    videos.append({"url": url, "title": title})
        
        return videos
    
    def get_video_title(self, video_url):
        """Get title for a single video"""
        cmd = ["yt-dlp", "--print", "title", video_url]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            # Fallback to URL-based title
            video_id = self.extract_video_id(video_url)
            return f"Video {video_id}" if video_id else "Unknown Video"
    
    def extract_video_id(self, url):
        """Extract video ID from YouTube URL"""
        patterns = [
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def read_videos_from_file(self, file_path):
        """Read video URLs from text file (one per line)"""
        videos = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if line and not line.startswith('#'):
                    try:
                        title = self.get_video_title(line)
                        videos.append({"url": line, "title": title})
                        print(f"✅ Added: {title}")
                    except Exception as e:
                        print(f"⚠️  Line {line_num}: Failed to get title for {line} - {e}")
                        videos.append({"url": line, "title": f"Video (line {line_num})"})
        return videos
    
    def add_playlist(self, playlist_id, playlist_title, playlist_url):
        """Add entire YouTube playlist"""
        manifest = self.load_manifest()
        
        try:
            videos_data = self.get_playlist_videos(playlist_url)
            
            # Create video entries
            videos = []
            for video_data in videos_data:
                videos.append({
                    "url": video_data["url"],
                    "title": video_data["title"],
                    "splits": 3,
                    "status": "pending",
                    "error": None,
                    "processed_files": []
                })
            
            # Add to manifest
            manifest["playlists"][playlist_id] = {
                "title": playlist_title,
                "url": playlist_url,
                "videos": videos
            }
            
            self.save_manifest(manifest)
            print(f"✅ Added playlist '{playlist_title}' with {len(videos)} videos")
            
        except Exception as e:
            print(f"❌ Failed to add playlist: {e}")
    
    def add_video_list(self, playlist_id, playlist_title, video_sources):
        """Add videos from files or URLs to playlist"""
        manifest = self.load_manifest()
        
        # Initialize playlist if it doesn't exist
        if playlist_id not in manifest["playlists"]:
            manifest["playlists"][playlist_id] = {
                "title": playlist_title,
                "url": None,
                "videos": []
            }
        
        videos = manifest["playlists"][playlist_id]["videos"]
        
        for source in video_sources:
            if Path(source).exists():
                # Read from file
                print(f"📄 Reading videos from: {source}")
                file_videos = self.read_videos_from_file(source)
                videos.extend(file_videos)
            else:
                # Single video URL
                try:
                    title = self.get_video_title(source)
                    videos.append({
                        "url": source,
                        "title": title,
                        "splits": 3,
                        "status": "pending", 
                        "error": None,
                        "processed_files": []
                    })
                    print(f"✅ Added: {title}")
                except Exception as e:
                    print(f"⚠️  Failed to get title for {source}: {e}")
                    videos.append({
                        "url": source,
                        "title": "Unknown Video",
                        "splits": 3,
                        "status": "pending",
                        "error": None,
                        "processed_files": []
                    })
        
        self.save_manifest(manifest)
        total_videos = len(videos)
        print(f"✅ Playlist '{playlist_title}' now has {total_videos} videos")
    
    def show_status(self):
        """Show current manifest status"""
        manifest = self.load_manifest()
        
        if not manifest["playlists"]:
            print("📋 No playlists in manifest")
            return
        
        print("📋 Current Manifest Status:\n")
        
        for playlist_id, playlist_data in manifest["playlists"].items():
            print(f"📁 {playlist_data['title']} ({playlist_id})")
            
            status_counts = {}
            for video in playlist_data["videos"]:
                status = video["status"]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            for status, count in status_counts.items():
                emoji = {"pending": "⏳", "processing": "🔄", "completed": "✅", "failed": "❌"}.get(status, "❓")
                print(f"   {emoji} {status}: {count}")
            
            print(f"   📊 Total: {len(playlist_data['videos'])} videos\n")

def main():
    parser = argparse.ArgumentParser(description="Add videos to processing manifest")
    parser.add_argument("--playlist", required=True, help="Playlist ID/name")
    parser.add_argument("--title", help="Playlist display title (defaults to playlist ID)")
    
    # Mutually exclusive group for input methods
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--url", help="YouTube playlist URL")
    input_group.add_argument("--video", help="Single video URL")
    input_group.add_argument("--videos", nargs="+", help="Video files or URLs")
    input_group.add_argument("--status", action="store_true", help="Show current manifest status")
    
    args = parser.parse_args()
    
    # Get base directory
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    manager = ManifestManager(base_dir)
    
    if args.status:
        manager.show_status()
        return
    
    playlist_title = args.title or args.playlist.replace('_', ' ').title()
    
    try:
        if args.url:
            # Add entire playlist
            manager.add_playlist(args.playlist, playlist_title, args.url)
        
        elif args.video:
            # Add single video
            manager.add_video_list(args.playlist, playlist_title, [args.video])
        
        elif args.videos:
            # Add multiple videos/files
            manager.add_video_list(args.playlist, playlist_title, args.videos)
        
        print(f"\n💡 Next step: python scripts/main.py 2  # Process 2 videos")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()