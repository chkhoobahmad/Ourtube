#!/usr/bin/env python3
import subprocess
import os
import re
import sys
import time
import shutil
from pathlib import Path

# ============================================================
# CONFIGURATION
# ============================================================
CHANNEL_URL = os.environ.get('CHANNEL_URL', '')
MAX_VIDEOS = int(os.environ.get('MAX_VIDEOS', '0')) if os.environ.get('MAX_VIDEOS', '0') != '0' else None
QUALITY = os.environ.get('YT_QUALITY', 'best')
ZIP_PASSWORD = os.environ.get('YT_PASSWORD', '')
DOWNLOAD_SUBS = os.environ.get('DOWNLOAD_SUBS', 'false') == 'true'
REPO_OWNER = os.environ.get('REPO_OWNER', '')
REPO_NAME = os.environ.get('REPO_NAME', '')
BRANCH = os.environ.get('BRANCH', '')

SPLIT_MB = 95
SPLIT_BYTES = SPLIT_MB * 1024 * 1024
BACKUP_DIR = f"/tmp/video_backup_{os.getpid()}"
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs("videos", exist_ok=True)

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def sanitize_name(name):
    """Sanitize folder/file name - limit length to 100 chars"""
    # Replace spaces and unwanted chars
    name = name.replace(' ', '-').replace('　', '-')
    # Remove invalid characters for filenames
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    # Replace multiple dashes/underscores with single
    name = re.sub(r'[-_]+', '-', name)
    # Remove leading/trailing special chars
    name = name.strip('-_')
    # Limit length to 100 characters
    if len(name) > 100:
        name = name[:100]
    # Ensure non-empty
    if not name:
        name = "video"
    return name

def urlencode(s):
    import urllib.parse
    return urllib.parse.quote(s, safe='')

def get_random_word():
    words = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "theta", "kappa", "lambda", "sigma", "omega", "nova", "star", "moon", "sun", "sky", "cloud", "river", "ocean", "mountain"]
    import random
    return f"{random.choice(words)}_{random.randint(1, 9999)}"

def get_format():
    if QUALITY == "audio":
        return "bestaudio/bestaudio*/best"
    elif QUALITY == "best":
        return "bestvideo+bestaudio/bestvideo*+bestaudio*/best"
    elif QUALITY in ["2160", "4k"]:
        return "bestvideo[height<=2160]+bestaudio/bestvideo[height<=2160]*+bestaudio*/bestvideo+bestaudio/best"
    elif QUALITY in ["1440", "2k"]:
        return "bestvideo[height<=1440]+bestaudio/bestvideo[height<=1440]*+bestaudio*/bestvideo+bestaudio/best"
    elif QUALITY == "1080":
        return "bestvideo[height<=1080]+bestaudio/bestvideo[height<=1080]*+bestaudio*/bestvideo+bestaudio/best"
    elif QUALITY == "720":
        return "bestvideo[height<=720]+bestaudio/bestvideo[height<=720]*+bestaudio*/bestvideo+bestaudio/best"
    elif QUALITY == "480":
        return "bestvideo[height<=480]+bestaudio/bestvideo[height<=480]*+bestaudio*/bestvideo+bestaudio/best"
    else:
        return "bestvideo+bestaudio/bestvideo*+bestaudio*/best"

def download_video(method, url, tmp_dir):
    fmt = get_format()
    
    if QUALITY == "audio":
        common_flags = f"--extract-audio --audio-format mp3 --audio-quality 0 --write-thumbnail --convert-thumbnails jpg --no-cache-dir --output {tmp_dir}/%(title)s.%(ext)s --no-part --no-playlist --retries 5 --fragment-retries 5 --no-check-certificates --concurrent-fragments 8 --buffer-size 16K --http-chunk-size 10M --progress --newline"
    elif QUALITY == "best":
        common_flags = f"--merge-output-format mp4 --format-sort res,+codec:vp9.1,+size --write-thumbnail --convert-thumbnails jpg --no-cache-dir --output {tmp_dir}/%(title)s.%(ext)s --no-part --no-playlist --retries 5 --fragment-retries 5 --no-check-certificates --concurrent-fragments 8 --buffer-size 16K --http-chunk-size 10M --progress --newline"
    else:
        common_flags = f"--merge-output-format mp4 --write-thumbnail --convert-thumbnails jpg --no-cache-dir --output {tmp_dir}/%(title)s.%(ext)s --no-part --no-playlist --retries 5 --fragment-retries 5 --no-check-certificates --concurrent-fragments 8 --buffer-size 16K --http-chunk-size 10M --progress --newline"

    commands = {
        1: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:github --user-agent \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36\" --add-header \"Accept-Language:en-US,en;q=0.9\" \"{url}\"",
        2: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:npm --user-agent \"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36\" --add-header \"Accept-Language:en-US,en;q=0.9\" \"{url}\"",
        3: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=web,mweb,android_vr --js-runtimes deno --remote-components ejs:github \"{url}\"",
        4: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=mweb \"{url}\"",
        5: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=android_vr \"{url}\"",
        6: f"yt-dlp --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=web --js-runtimes deno --remote-components ejs:github \"{url}\"",
        7: f"yt-dlp --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=mweb \"{url}\"",
        8: f"yt-dlp --proxy socks5://127.0.0.1:1080 --format \"{fmt}\" {common_flags} --extractor-args youtube:player_client=android --user-agent \"Mozilla/5.0 (Linux; Android 12; SM-S906N Build/QP1A.190711.020) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36\" \"{url}\""
    }
    
    print(f"Trying download method {method}...")
    result = subprocess.run(commands[method], shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        return True
    return False

# ============================================================
# GET CHANNEL NAME
# ============================================================
print(f"Getting channel name from: {CHANNEL_URL}")

# Try multiple methods to get channel name
channel_name = ""

# Method 1: With proxy
try:
    result = subprocess.run(["yt-dlp", "--proxy", "socks5://127.0.0.1:1080", "--quiet", "--print", "%(channel)s", CHANNEL_URL], capture_output=True, text=True, timeout=30)
    if result.stdout.strip():
        channel_name = result.stdout.strip()
        print(f"Got channel name via proxy: {channel_name}")
except:
    pass

# Method 2: Without proxy
if not channel_name:
    try:
        result = subprocess.run(["yt-dlp", "--quiet", "--print", "%(channel)s", CHANNEL_URL], capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            channel_name = result.stdout.strip()
            print(f"Got channel name without proxy: {channel_name}")
    except:
        pass

# Method 3: Extract from URL
if not channel_name:
    # Try to get channel ID
    try:
        result = subprocess.run(["yt-dlp", "--quiet", "--print", "%(channel_id)s", CHANNEL_URL], capture_output=True, text=True, timeout=30)
        if result.stdout.strip():
            channel_name = result.stdout.strip()
            print(f"Got channel ID: {channel_name}")
    except:
        pass

# Method 4: Parse from URL
if not channel_name:
    match = re.search(r'@([^/?]+)', CHANNEL_URL)
    if match:
        channel_name = match.group(1)
        print(f"Extracted from URL: {channel_name}")
    else:
        channel_name = "unknown_channel"

# Clean channel name - limit to 50 chars and remove special chars
channel_name = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF]', '_', channel_name)
channel_name = re.sub(r'_+', '_', channel_name).strip('_')
# Limit to 50 characters
if len(channel_name) > 50:
    channel_name = channel_name[:50]
# Ensure non-empty
if not channel_name:
    channel_name = "channel"

print(f"Final channel name: {channel_name}")

CHANNEL_DIR = f"videos/{channel_name}"
BACKUP_CHANNEL_DIR = f"{BACKUP_DIR}/{channel_name}"
os.makedirs(CHANNEL_DIR, exist_ok=True)
os.makedirs(BACKUP_CHANNEL_DIR, exist_ok=True)

# ============================================================
# GET VIDEO LIST
# ============================================================
print("Fetching video list from channel...")

video_urls = []
cmd = ["yt-dlp", "--proxy", "socks5://127.0.0.1:1080", "--flat-playlist", "--print", "%(url)s", CHANNEL_URL]
if MAX_VIDEOS:
    cmd.extend(["--max-downloads", str(MAX_VIDEOS)])

try:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode == 0 and result.stdout.strip():
        video_urls = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]
except:
    pass

# Try without proxy
if not video_urls:
    cmd = ["yt-dlp", "--flat-playlist", "--print", "%(url)s", CHANNEL_URL]
    if MAX_VIDEOS:
        cmd.extend(["--max-downloads", str(MAX_VIDEOS)])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.stdout.strip():
            video_urls = [u.strip() for u in result.stdout.strip().split('\n') if u.strip()]
    except:
        pass

total_videos = len(video_urls)
print(f"Total videos found: {total_videos}")

if total_videos == 0:
    print("No videos found in channel!")
    sys.exit(1)

# ============================================================
# SAVE VIDEO INFO FOR SUBTITLES
# ============================================================
video_info_file = "/tmp/video_info.txt"
open(video_info_file, 'w').close()

# ============================================================
# MAIN DOWNLOAD LOOP
# ============================================================
for idx, video_url in enumerate(video_urls, 1):
    print(f"\n{'='*60}")
    print(f"Processing video {idx}/{total_videos}: {video_url}")
    print(f"{'='*60}")
    
    tmp_dir = f"tmp_downloads_{idx}"
    os.makedirs(tmp_dir, exist_ok=True)
    
    download_success = False
    for method in range(1, 9):
        if download_video(method, video_url, tmp_dir):
            print(f"Download successful with method {method}!")
            
            quality_ok = True
            if QUALITY not in ["best", "audio"] and QUALITY.isdigit():
                target_height = int(QUALITY)
                for f in Path(tmp_dir).glob("*.mp4"):
                    if f.is_file():
                        result = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height", "-of", "csv=p=0", str(f)], capture_output=True, text=True)
                        actual_height = result.stdout.strip()
                        if actual_height and actual_height.isdigit() and int(actual_height) < target_height - 150:
                            print(f"Method {method} delivered {actual_height}p instead of {target_height}p — rejecting...")
                            quality_ok = False
                            f.unlink()
            
            if quality_ok:
                download_success = True
                break
        else:
            print(f"Method {method} failed, waiting 3 seconds...")
            time.sleep(3)
    
    if not download_success:
        print(f"All download methods failed for video: {video_url} — skipping.")
        shutil.rmtree(tmp_dir, ignore_errors=True)
        continue
    
    for f in Path(tmp_dir).glob("*.part"):
        f.unlink()
    
    for file in Path(tmp_dir).iterdir():
        if file.is_file() and file.suffix.lower() not in ['.jpg', '.webp']:
            size = file.stat().st_size
            basename = file.name
            filename_no_ext = file.stem
            ext = file.suffix[1:]
            filename_no_ext = sanitize_name(filename_no_ext)
            
            final_folder_name = filename_no_ext
            counter = 1
            while (Path(CHANNEL_DIR) / final_folder_name).exists() or (Path(BACKUP_CHANNEL_DIR) / final_folder_name).exists():
                suffix = get_random_word()
                final_folder_name = f"{filename_no_ext}_{suffix}"
                # Limit length
                if len(final_folder_name) > 100:
                    final_folder_name = final_folder_name[:100]
                counter += 1
            
            video_backup_dir = Path(BACKUP_CHANNEL_DIR) / final_folder_name
            video_backup_dir.mkdir(parents=True, exist_ok=True)
            
            thumb_files = list(Path(tmp_dir).glob("*.jpg"))
            if thumb_files:
                shutil.copy(thumb_files[0], video_backup_dir / "thumbnail.jpg")
            
            with open(video_info_file, 'a') as f:
                f.write(f"{video_url}|{filename_no_ext}|{final_folder_name}\n")
            
            folder_encoded = urlencode(final_folder_name)
            channel_encoded = urlencode(channel_name)
            
            if size > SPLIT_BYTES:
                archive_base = video_backup_dir / final_folder_name
                if ZIP_PASSWORD:
                    subprocess.run(["7z", "a", "-tzip", f"-v{SPLIT_MB}m", f"-p{ZIP_PASSWORD}", "-mx=0", f"{archive_base}.zip", str(file)], check=False)
                else:
                    subprocess.run(["zip", "-0", "-s", f"{SPLIT_MB}m", f"{archive_base}.zip", str(file)], check=False)
                
                part_count = len(list(video_backup_dir.glob("*.zip*")))
                total_size = sum(f.stat().st_size for f in video_backup_dir.iterdir() if f.is_file())
                total_size_mb = total_size / 1024 / 1024
                
                download_links_md = ""
                link_num = 0
                for part_file in sorted(video_backup_dir.glob("*.zip*")):
                    part_basename = part_file.name
                    part_encoded = urlencode(part_basename)
                    raw_link = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/videos/{channel_encoded}/{folder_encoded}/{part_encoded}"
                    link_num += 1
                    download_links_md += f"| {link_num} | `{part_basename}` | [Download]({raw_link}) |\n"
                
                readme_content = f"""# {filename_no_ext}

<div align="center">
  <picture>
    <img src="thumbnail.jpg" width="250" />
  </picture>
</div>

<br>

---

## Video Information

| Property | Value |
|----------|-------|
| **Video Name** | `{filename_no_ext}` |
| **Channel** | `{channel_name}` |
| **Original Link** | [YouTube Video]({video_url}) |
| **Total Size** | **{part_count} parts** - **{total_size_mb:.2f} MB** |
| **Quality** | **{QUALITY}** |
| **Status** | **Complete (100%)** |
| **Password Protected** | **{'YES' if ZIP_PASSWORD else 'NO'}** |

---

## Download Links

> Download **all parts**, then open `{final_folder_name}.zip` — the other parts are found automatically.

| # | File | Link |
|---|------|------|
{download_links_md}

---

## How to Extract

| OS | Steps |
|----|-------|
| **Windows** | Right-click `{final_folder_name}.zip` → Extract Here (needs 7-Zip or WinRAR) {f'→ enter password' if ZIP_PASSWORD else ''} |
| **Mac** | Open with Keka → {f'enter password' if ZIP_PASSWORD else 'extract'} |
| **Linux** | `unzip {final_folder_name}.zip` {f'→ enter password' if ZIP_PASSWORD else ''} |
| **Android** | Use ZArchiver → tap `{final_folder_name}.zip` {f'→ enter password' if ZIP_PASSWORD else ''} |

---

*This tool created by [avasam.ir](https://avasam.ir)*
"""
                (video_backup_dir / "README.md").write_text(readme_content, encoding='utf-8')
                print(f"Created README.md with {part_count} parts")
            
            else:
                if ZIP_PASSWORD:
                    subprocess.run(["zip", "-0", "-P", ZIP_PASSWORD, str(video_backup_dir / f"{final_folder_name}.zip"), str(file)], check=False)
                    size_mb = size / 1024 / 1024
                    file_encoded = urlencode(f"{final_folder_name}.zip")
                    raw_link = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/videos/{channel_encoded}/{folder_encoded}/{file_encoded}"
                    
                    readme_content = f"""# {filename_no_ext}

<div align="center">
  <picture>
    <img src="thumbnail.jpg" width="250" />
  </picture>
</div>

<br>

---

## Video Information

| Property | Value |
|----------|-------|
| **Video Name** | `{filename_no_ext}` |
| **Channel** | `{channel_name}` |
| **Original Link** | [YouTube Video]({video_url}) |
| **Total Size** | **1 archive** - **{size_mb:.2f} MB** |
| **Quality** | **{QUALITY}** |
| **Status** | **Complete (100%)** |
| **Password Protected** | **YES** |

---

## Download Link

| # | File | Link |
|---|------|------|
| 1 | `{final_folder_name}.zip` | [Download]({raw_link}) |

---

## How to Extract

| OS | Steps |
|----|-------|
| **Windows** | Double-click `{final_folder_name}.zip` → enter password |
| **Mac** | Double-click → enter password |
| **Linux** | `unzip {final_folder_name}.zip` → enter password |
| **Android** | Tap the file → enter password |

---

*This tool created by [avasam.ir](https://avasam.ir)*
"""
                    (video_backup_dir / "README.md").write_text(readme_content, encoding='utf-8')
                    print("Created password-protected zip archive and README.md")
                
                else:
                    shutil.copy(file, video_backup_dir / f"{final_folder_name}.{ext}")
                    size_mb = size / 1024 / 1024
                    file_encoded = urlencode(f"{final_folder_name}.{ext}")
                    raw_link = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/videos/{channel_encoded}/{folder_encoded}/{file_encoded}"
                    
                    readme_content = f"""# {filename_no_ext}

<div align="center">
  <picture>
    <img src="thumbnail.jpg" width="250" />
  </picture>
</div>

<br>

---

## Video Information

| Property | Value |
|----------|-------|
| **Video Name** | `{filename_no_ext}` |
| **Channel** | `{channel_name}` |
| **Original Link** | [YouTube Video]({video_url}) |
| **Total Size** | **1 file** - **{size_mb:.2f} MB** |
| **Quality** | **{QUALITY}** |
| **Status** | **Complete (100%)** |
| **Password Protected** | **NO** |

---

## Download Link

| # | File | Link |
|---|------|------|
| 1 | `{final_folder_name}.{ext}` | [Download]({raw_link}) |

---

Ready to use — no extraction needed!

---

*This tool created by [avasam.ir](https://avasam.ir)*
"""
                    (video_backup_dir / "README.md").write_text(readme_content, encoding='utf-8')
                    print("Copied file and created README.md")
    
    shutil.rmtree(tmp_dir, ignore_errors=True)
    print(f"Video {idx}/{total_videos} completed")

with open("/tmp/backup_dir_path.txt", "w") as f:
    f.write(BACKUP_DIR)
with open("/tmp/env_vars.txt", "w") as f:
    f.write(f"REPO_OWNER={REPO_OWNER}\n")
    f.write(f"REPO_NAME={REPO_NAME}\n")
    f.write(f"BRANCH={BRANCH}\n")
    f.write(f"CHANNEL_NAME={channel_name}\n")

print(f"\n{'='*60}")
print(f"ALL VIDEOS PROCESSED! Total: {total_videos}")
print(f"{'='*60}")
