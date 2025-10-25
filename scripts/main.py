#!/usr/bin/env python3
"""
Chinese Video Processor - Main Processing Script
Processes pending videos in manifest.json

Usage: 
  python scripts/main.py           # Process all pending videos
  python scripts/main.py 2         # Process next 2 pending videos
  python scripts/main.py --count 5 # Process next 5 pending videos
"""

import json
import os
import sys
import subprocess
from pathlib import Path
from openai import OpenAI
import tempfile
import shutil
from datetime import datetime
import argparse

class VideoProcessor:
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.manifest_file = self.base_dir / "manifest.json"
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            print("❌ Error: OPENAI_API_KEY environment variable not set")
            sys.exit(1)
    
    def load_manifest(self):
        """Load manifest file"""
        if not self.manifest_file.exists():
            print(f"❌ Manifest file not found: {self.manifest_file}")
            sys.exit(1)
        
        with open(self.manifest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_manifest(self, manifest):
        """Save manifest file"""
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    
    def update_video_status(self, playlist_id, video_idx, status, error=None, processed_files=None):
        """Update video status in manifest"""
        manifest = self.load_manifest()
        video = manifest["playlists"][playlist_id]["videos"][video_idx]
        video["status"] = status
        if error:
            video["error"] = error
        if processed_files:
            video["processed_files"] = processed_files
        self.save_manifest(manifest)
        print(f"📝 Updated status: {status}")
    
    def download_video(self, url, output_dir):
        """Download video with low quality video + high quality audio"""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            "yt-dlp",
            "--format", "worst[height<=480]+bestaudio/worst",
            "--merge-output-format", "mp4",
            "--output", str(output_dir / "%(title)s.%(ext)s"),
            "--concurrent-fragments", "8",
            url
        ]
        
        print(f"📥 Downloading: {url}")
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            # Find downloaded file
            video_file = max(output_dir.glob("*.mp4"), key=lambda f: f.stat().st_mtime)
            print(f"✅ Downloaded: {video_file.name}")
            return video_file
        else:
            raise Exception(f"Download failed: {result.stderr}")
    
    def download_audio_for_transcription(self, url, temp_dir):
        """Download high quality audio for transcription"""
        cmd = [
            "yt-dlp",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",  # Highest quality for transcription
            "--format", "bestaudio",
            "--output", str(temp_dir / "%(title)s.%(ext)s"),
            url
        ]
        
        print(f"🎧 Downloading audio for transcription...")
        result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            audio_file = next(temp_dir.glob("*.mp3"))
            return audio_file
        else:
            raise Exception(f"Audio download failed: {result.stderr}")
    
    def split_audio_if_needed(self, audio_file, chunk_duration=300):
        """Split large audio files for Whisper API"""
        file_size_mb = audio_file.stat().st_size / (1024 * 1024)
        print(f"📊 Audio size: {file_size_mb:.1f}MB")
        
        if file_size_mb <= 25:
            print("🎯 Direct transcription (small file)")
            return [audio_file]
        
        print("📏 Splitting large audio file...")
        temp_dir = audio_file.parent
        
        cmd = [
            "ffmpeg", "-i", str(audio_file),
            "-f", "segment", "-segment_time", str(chunk_duration),
            "-c", "copy", str(temp_dir / "chunk_%03d.mp3")
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"Audio splitting failed: {result.stderr}")
        
        chunks = sorted(temp_dir.glob("chunk_*.mp3"))
        print(f"✂️ Created {len(chunks)} audio chunks")
        return chunks
    
    def transcribe_audio(self, audio_files, chunk_duration=300):
        """Transcribe audio with Whisper API"""
        client = OpenAI(api_key=self.api_key)
        all_segments = []
        
        for i, audio_file in enumerate(audio_files):
            print(f"🗣️ Transcribing chunk {i+1}/{len(audio_files)}")
            
            with open(audio_file, "rb") as audio:
                transcript = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    language="zh",
                    response_format="verbose_json",
                    timestamp_granularities=["segment"]
                )
            
            # Adjust timestamps if multiple chunks
            time_offset = i * chunk_duration if len(audio_files) > 1 else 0
            
            for segment in transcript.segments:
                adjusted = type('obj', (object,), {
                    'start': segment.start + time_offset,
                    'end': segment.end + time_offset,
                    'text': segment.text
                })()
                all_segments.append(adjusted)
        
        return all_segments
    
    def generate_srt(self, segments, output_file):
        """Generate SRT file from segments"""
        def format_time(seconds):
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            s = int(seconds % 60)
            ms = int((seconds % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments):
                f.write(f"{i + 1}\n")
                f.write(f"{format_time(segment.start)} --> {format_time(segment.end)}\n")
                f.write(f"{segment.text.strip()}\n\n")
        
        print(f"📄 Generated SRT: {output_file.name}")
    
    def get_video_duration(self, video_file):
        """Get video duration in seconds"""
        cmd = [
            "ffprobe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "csv=p=0", str(video_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
        return None
    
    def split_video(self, video_file, num_parts, output_dir):
        """Split video into parts"""
        duration = self.get_video_duration(video_file)
        if not duration:
            raise Exception("Could not get video duration")
        
        part_duration = duration / num_parts
        print(f"✂️ Splitting video into {num_parts} parts ({part_duration/60:.1f}min each)")
        
        base_name = video_file.stem
        output_files = []
        
        for i in range(num_parts):
            start_time = i * part_duration
            output_file = output_dir / f"{base_name}_part{i+1}.mp4"
            
            cmd = [
                "ffmpeg", "-i", str(video_file),
                "-ss", str(start_time), "-t", str(part_duration),
                "-c", "copy", "-avoid_negative_ts", "make_zero",
                str(output_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Created: {output_file.name}")
                output_files.append(output_file)
            else:
                raise Exception(f"Video split failed: {result.stderr}")
        
        return output_files, part_duration
    
    def split_srt(self, segments, num_parts, total_duration, output_dir, base_name):
        """Split SRT segments into parts"""
        part_duration = total_duration / num_parts
        output_files = []
        
        for part_num in range(num_parts):
            part_start = part_num * part_duration
            part_end = (part_num + 1) * part_duration
            
            part_segments = []
            subtitle_counter = 1
            
            for segment in segments:
                if segment.start < part_end and segment.end > part_start:
                    adjusted_start = max(0, segment.start - part_start)
                    adjusted_end = min(part_duration, segment.end - part_start)
                    
                    if adjusted_end > adjusted_start:
                        adjusted = type('obj', (object,), {
                            'start': adjusted_start,
                            'end': adjusted_end,
                            'text': segment.text
                        })()
                        part_segments.append(adjusted)
            
            if part_segments:
                srt_file = output_dir / f"{base_name}_part{part_num + 1}.srt"
                self.generate_srt(part_segments, srt_file)
                output_files.append(srt_file)
        
        return output_files
    
    def process_video(self, playlist_id, video_idx, video_data):
        """Process a single video"""
        url = video_data["url"]
        splits = video_data.get("splits", 3)
        
        print(f"\n🎬 Processing: {video_data.get('title', 'Unknown')}")
        print(f"📋 Splits: {splits}")
        
        # Setup directories
        playlist_dir = self.base_dir / "playlists" / playlist_id
        video_dir = playlist_dir / "videos"
        processed_dir = playlist_dir / "processed"
        temp_dir = playlist_dir / "temp"
        
        for dir in [video_dir, processed_dir, temp_dir]:
            dir.mkdir(parents=True, exist_ok=True)
        
        try:
            self.update_video_status(playlist_id, video_idx, "processing")
            
            # Download video
            video_file = self.download_video(url, video_dir)
            video_duration = self.get_video_duration(video_file)
            
            # Download and transcribe audio
            with tempfile.TemporaryDirectory() as temp_audio_dir:
                temp_path = Path(temp_audio_dir)
                audio_file = self.download_audio_for_transcription(url, temp_path)
                audio_chunks = self.split_audio_if_needed(audio_file)
                segments = self.transcribe_audio(audio_chunks)
            
            # Split video and SRT
            video_parts, part_duration = self.split_video(video_file, splits, processed_dir)
            srt_parts = self.split_srt(segments, splits, video_duration, processed_dir, video_file.stem)
            
            # Track processed files
            processed_files = []
            for video_part, srt_part in zip(video_parts, srt_parts):
                processed_files.append({
                    "video": str(video_part.relative_to(self.base_dir)),
                    "srt": str(srt_part.relative_to(self.base_dir))
                })
            
            self.update_video_status(playlist_id, video_idx, "completed", processed_files=processed_files)
            
            print(f"✅ Completed: {len(processed_files)} parts ready for Language Reactor!")
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Failed: {error_msg}")
            self.update_video_status(playlist_id, video_idx, "failed", error=error_msg)
        
        finally:
            # Cleanup temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def run(self, max_videos=None):
        """Process pending videos in manifest"""
        manifest = self.load_manifest()
        
        # Count total pending
        total_pending = 0
        for playlist_data in manifest["playlists"].values():
            total_pending += sum(1 for v in playlist_data["videos"] if v["status"] == "pending")
        
        if total_pending == 0:
            print("✅ No pending videos to process!")
            return
        
        # Determine how many to process
        to_process = min(max_videos, total_pending) if max_videos else total_pending
        
        print(f"📊 Found {total_pending} pending videos")
        print(f"🚀 Processing next {to_process} videos...")
        
        processed_count = 0
        
        # Process videos in order across all playlists
        for playlist_id, playlist_data in manifest["playlists"].items():
            if processed_count >= to_process:
                break
                
            print(f"\n📁 Playlist: {playlist_data['title']}")
            
            for video_idx, video_data in enumerate(playlist_data["videos"]):
                if processed_count >= to_process:
                    break
                    
                if video_data["status"] == "pending":
                    print(f"\n[{processed_count + 1}/{to_process}] Processing video...")
                    self.process_video(playlist_id, video_idx, video_data)
                    processed_count += 1
        
        remaining = total_pending - processed_count
        print(f"\n🎉 Processed {processed_count} videos!")
        if remaining > 0:
            print(f"📋 {remaining} videos still pending. Run again to continue.")
        print("📁 Check playlists/ directories for results.")

def main():
    parser = argparse.ArgumentParser(description="Process Chinese videos for Language Reactor")
    parser.add_argument("count", nargs="?", type=int, help="Number of videos to process (default: all)")
    parser.add_argument("--count", type=int, help="Number of videos to process")
    
    args = parser.parse_args()
    
    # Use positional or --count argument
    max_videos = args.count or getattr(args, 'count', None)
    
    # Get the base directory (parent of scripts/)
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    processor = VideoProcessor(base_dir)
    processor.run(max_videos)

if __name__ == "__main__":
    main()