#!/usr/bin/env python3
import subprocess
import os
import re
import time
import shutil
from pathlib import Path

with open("/tmp/backup_dir_path.txt", "r") as f:
    BACKUP_DIR = f.read().strip()
with open("/tmp/env_vars.txt", "r") as f:
    for line in f:
        if '=' in line:
            key, val = line.strip().split('=', 1)
            os.environ[key] = val

REPO_OWNER = os.environ.get('REPO_OWNER', '')
REPO_NAME = os.environ.get('REPO_NAME', '')
BRANCH = os.environ.get('BRANCH', '')
CHANNEL_NAME = os.environ.get('CHANNEL_NAME', '')
BACKUP_CHANNEL_DIR = f"{BACKUP_DIR}/{CHANNEL_NAME}"
video_info_file = "/tmp/video_info.txt"

def sub_download(mode, out_template, url):
    sub_flags = {
        'all': '--write-sub --sub-langs fa,en',
        'fa-native': '--write-sub --sub-langs fa',
        'fa-auto': '--write-auto-sub --sub-langs fa',
        'en-auto': '--write-auto-sub --sub-langs en',
        'auto-both': '--write-auto-sub --sub-langs en,fa'
    }
    sflags = sub_flags.get(mode, '--write-sub --sub-langs fa,en')
    common = f"--sub-format vtt/srt/best --convert-subs vtt --skip-download --no-playlist --no-check-certificates --output {out_template}"
    
    commands = [
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:github --user-agent 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36' {sflags} {common} '{url}'",
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:npm {sflags} {common} '{url}'",
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=web,mweb,android_vr --js-runtimes deno --remote-components ejs:github {sflags} {common} '{url}'",
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=mweb {sflags} {common} '{url}'",
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=android_vr {sflags} {common} '{url}'",
        f"yt-dlp --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:github {sflags} {common} '{url}'",
        f"yt-dlp --extractor-args youtube:player_client=mweb {sflags} {common} '{url}'",
        f"yt-dlp --proxy socks5://127.0.0.1:1080 --extractor-args youtube:player_client=android --user-agent 'Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36' {sflags} {common} '{url}'"
    ]
    
    for i, cmd in enumerate(commands, 1):
        print(f"  [subtitle] method {i} ...")
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        sub_dir = Path(out_template).parent
        if mode in ['fa-native', 'fa-auto']:
            fa_files = list(sub_dir.glob("*.fa.*"))
            if fa_files:
                return True
        elif mode == 'en-auto':
            en_files = list(sub_dir.glob("*.en.*"))
            if en_files:
                return True
        elif mode == 'auto-both':
            en_files = list(sub_dir.glob("*.en.*"))
            fa_files = list(sub_dir.glob("*.fa.*"))
            if en_files and fa_files:
                return True
        else:
            sub_files = list(sub_dir.glob("*.vtt")) + list(sub_dir.glob("*.srt"))
            if sub_files:
                return True
        time.sleep(1)
    return False

with open(video_info_file, 'r') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) != 3:
            continue
        video_url, video_name, folder_name = parts
        
        print(f"\n{'='*60}")
        print(f"Downloading subtitles for: {video_name}")
        print(f"{'='*60}")
        
        subtitle_dir = Path(BACKUP_CHANNEL_DIR) / folder_name / "subtitle"
        subtitle_dir.mkdir(parents=True, exist_ok=True)
        out_template = str(subtitle_dir / "%(title)s")
        
        sub_download("all", out_template, video_url)
        
        en_count = len(list(subtitle_dir.glob("*.en.*")))
        fa_count = len(list(subtitle_dir.glob("*.fa.*")))
        
        if en_count == 0 or fa_count == 0:
            sub_download("auto-both", out_template, video_url)
        
        sub_files = list(subtitle_dir.glob("*"))
        if not sub_files:
            print("  (no subtitles available for this video)")
            subtitle_dir.rmdir()
            continue
        
        print(f"\n→ Subtitle files downloaded ({len(sub_files)} file(s)):")
        for sf in sub_files:
            print(f"  • {sf.name}")
        
        zip_path = Path(BACKUP_CHANNEL_DIR) / folder_name / "subtitle.zip"
        print("\n→ Zipping subtitles → subtitle.zip ...")
        
        result = subprocess.run(f"cd {subtitle_dir} && zip -j {zip_path} ./*", shell=True, capture_output=True)
        if result.returncode == 0:
            shutil.rmtree(subtitle_dir)
            if zip_path.exists():
                zip_size = zip_path.stat().st_size / 1024 / 1024
                print(f"✅ subtitle.zip created ({zip_size:.2f} MB)")
                
                import urllib.parse
                channel_encoded = urllib.parse.quote(CHANNEL_NAME, safe='')
                folder_encoded = urllib.parse.quote(folder_name, safe='')
                sub_raw_link = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/videos/{channel_encoded}/{folder_encoded}/subtitle.zip"
                
                readme_path = Path(BACKUP_CHANNEL_DIR) / folder_name / "README.md"
                if readme_path.exists():
                    readme_content = readme_path.read_text(encoding='utf-8')
                    sub_section = f"""

---

## 🔤 Subtitles

| # | File | Link |
|---|------|------|
| 1 | `subtitle.zip` | [Download]({sub_raw_link}) |

> Contains all available subtitle languages. Extract to get `.vtt` files.
"""
                    if "## Download Link" in readme_content:
                        readme_content = readme_content.replace("## Download Link", f"{sub_section}\n\n## Download Link")
                    elif "## Download Links" in readme_content:
                        readme_content = readme_content.replace("## Download Links", f"{sub_section}\n\n## Download Links")
                    else:
                        readme_content += sub_section
                    
                    readme_path.write_text(readme_content, encoding='utf-8')
                    print("README patched with subtitle section")
        else:
            print("⚠️ Zip command failed - continuing without subtitles")
            shutil.rmtree(subtitle_dir, ignore_errors=True)

print("\n✅ Subtitle download phase complete")
