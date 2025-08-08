# utils.py

import aiohttp
import asyncio
import logging
import os
import re
import urllib.parse
import random
from urllib.parse import quote
import requests
from plugins.api import SpotMate
import random




logger = logging.getLogger(__name__)

def safe_filename(name: str) -> str:
    """Remove unsafe filesystem characters from a filename."""
    return re.sub(r'[\\/*?:"<>|]', '_', name)

import asyncio

aria2c_semaphore = asyncio.Semaphore(1)  # max 1 parallel

async def download_with_aria2c(url, output_dir, filename):
    async with aria2c_semaphore:
        # optional small delay before starting
        await asyncio.sleep(2)

        cmd = [
            "aria2c",
            "-x", "2",
            "-s", "2",
            "-k", "1M",
            "--max-tries=5",
            "--retry-wait=5",
            "--timeout=60",
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            "-d", output_dir,
            "-o", filename,
            url
        ]
       
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

   
        if process.returncode == 0:
         
            return True
        else:
            logger.error(f"aria2c failed with exit code {process.returncode}")
            # optionally implement exponential backoff retry here
            return False



def ms_to_minutes(ms):
    total_seconds = ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{str(seconds).zfill(2)}"

import aiohttp
import asyncio

import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

import aiohttp
import asyncio
import logging
import re

import aiohttp
import asyncio
import re

async def spotify_download_primary(url):
    if "spotify.com" not in url:
        return {"error": "URL must be from Spotify"}

    base_url = "https://api.fabdl.com"
    media = "spotify"

    async with aiohttp.ClientSession() as session:
        try:
            # Step 1: Get track info
            get_url = f"{base_url}/{media}/get?url={aiohttp.helpers.quote(url)}"
            async with session.get(get_url) as resp:
                data = await resp.json()
            if not data.get("result"):
                return {"error": "Failed to get song info"}

            result = data["result"]
            if result.get("type") == "track":
                result["tracks"] = [result]

            track = result["tracks"][0]
            if not track or not track.get("id") or not result.get("gid"):
                return {"error": "Song ID not found"}

            # Step 2: Start conversion
            convert_url = f"{base_url}/{media}/mp3-convert-task/{result['gid']}/{track['id']}"
            async with session.get(convert_url) as resp:
                convert_data = await resp.json()
            if not convert_data.get("result"):
                return {"error": "Failed to start conversion"}

            tid = convert_data["result"]["tid"]
            progress_url = f"{base_url}/{media}/mp3-convert-progress/{tid}"

            # Step 3: Poll conversion progress
            while True:
                await asyncio.sleep(1)
                async with session.get(progress_url) as resp:
                    progress_data = await resp.json()

                if not progress_data.get("result"):
                    return {"error": "Failed to get conversion progress"}

                status = progress_data["result"].get("status")
                if status == 3:
                    download_url = f"{base_url}{progress_data['result'].get('download_url')}"

                    # Artist name handling fix:
                    artists = track.get("artists", [])

                    # Agar artist string ke roop me aaye, to usko list me daalo
                    if isinstance(artists, str):
                        artists = [artists]

                    artist_names = []
                    for artist in artists:
                        if isinstance(artist, dict):
                            name = artist.get("name", "Unknown")
                        else:
                            name = str(artist)

                        name = re.sub(r'[\*_~`]', '', name).strip()

                        name = name.replace('&', ',')
                        artist_names.append(name)

                    artist_str = ", ".join(artist_names)

                    return {
                        "title": track.get("name"),
                        "artist": artist_str,
                        "duration": track.get("duration_ms"),
                        "image": track.get("image") or result.get("image"),
                        "download": download_url
                    }
                elif status < 0:
                    return {"error": "Conversion failed"}

        except Exception as e:
            return {"error": f"Request error: {str(e)}"}

import asyncio
import random
import logging

logger = logging.getLogger(__name__)

async def get_song_download_url_by_spotify_url(url, max_retries=3, retry_delay=3):
    for attempt in range(1, max_retries + 1):
        methods = ['primary', 'secondary']
        random.shuffle(methods)

        first = methods[0]
        second = methods[1]

        try:
            if first == 'primary':
                # Direct await, no run_in_executor
                result = await asyncio.wait_for(spotify_download_primary(url), timeout=20)
                if result and result.get('download'):
                    return (
                        result['title'],
                        result['artist'],
                        result['duration'],
                        result['image'],
                        result['download']
                    )
            else:
                results = await asyncio.wait_for(spotify_download_secondary(url), timeout=20)

                if isinstance(results, list):
                    for item in results:
                        if item.get('download'):
                            result = item
                            return (
                                result['title'],
                                result['artist'],
                                result['duration'],
                                result['image'],
                                result['download']
                            )
        except Exception as e:
            logger.info(f"Attempt {attempt}: {first} method failed with error: {e}")

        try:
            if second == 'primary':
                result = await asyncio.wait_for(spotify_download_primary(url), timeout=20)
                if result and result.get('download'):
                    return (
                        result['title'],
                        result['artist'],
                        result['duration'],
                        result['image'],
                        result['download']
                    )
            else:
                results = await asyncio.wait_for(spotify_download_secondary(url), timeout=20)
                if isinstance(results, list):
                    for item in results:
                        if item.get('download'):
                            result = item
                            return (
                                result['title'],
                                result['artist'],
                                result['duration'],
                                result['image'],
                                result['download']
                            )
        except Exception as e:
            logger.info(f"Attempt {attempt}: {second} method failed with error: {e}")

        logger.info(f"Attempt {attempt} failed, retrying after {retry_delay} seconds...")
        await asyncio.sleep(retry_delay)

    return None, None, None, None, None




import aiohttp
import asyncio
from bs4 import BeautifulSoup

class SpotifyDownloaderSecondary:
    def __init__(self):
        self.base_url = "https://spotifydownloader.pro/"
        self.session = None
        self.cookies = None

    async def fetch_cookies(self):
        async with aiohttp.ClientSession() as session:
            async with session.get(self.base_url) as resp:
                # Extract cookies from response headers
                cookies = resp.cookies
                cookie_header = "; ".join([f"{key}={val.value}" for key, val in cookies.items()])
                self.cookies = cookie_header

    async def download(self, url):
        if not self.cookies:
            await self.fetch_cookies()

        headers = {
            "accept": "text/html,application/xhtml+xml;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "referer": self.base_url,
            "sec-fetch-mode": "navigate",
            "user-agent": "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
            "cookie": self.cookies,
            "content-type": "application/x-www-form-urlencoded",
            "origin": self.base_url,
        }

        data = f"url={aiohttp.helpers.quote(url)}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.base_url, data=data, headers=headers) as resp:
                    html = await resp.text()
                    return self.parse_response(html)
            except Exception as e:
                return {"error": f"Download failed: {str(e)}"}

    def parse_response(self, html):
        soup = BeautifulSoup(html, "html.parser")
        results = []

        rows = soup.select(".res_box tr")
        for tr in rows:
            title_tag = tr.select_one(".rb_title")
            artist_tag = tr.select_one(".rb_title em") or tr.select_one(".rb_title span")
            image = tr.select_one(".rb_icon")
            link = tr.select_one(".rb_btn")

            raw_title = title_tag.get_text(strip=True) if title_tag else "No Title"
            artist = artist_tag.get_text(strip=True) if artist_tag else "Unknown"

            # Title se parentheses aur unke beech ka content hatao
            cleaned_title = re.sub(r"\s*\(.*?\)", "", raw_title).strip()

            # Artist se parentheses hatao
            cleaned_artist = re.sub(r"[\(\)]", "", artist).strip()

            results.append({
                "title": cleaned_title,
                "artist": cleaned_artist,
                "image": image["src"] if image and image.has_attr("src") else "",
                "download": link["href"] if link and link.has_attr("href") else ""
            })

        return results

# Wrapper function for usage
async def spotify_download_secondary(url):
    downloader = SpotifyDownloaderSecondary()
    return await downloader.download(url)



async def download_thumbnail(thumb_url: str, output_path: str) -> bool:
    if not thumb_url:
        return False

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumb_url) as resp:
                if resp.status == 200:
                    with open(output_path, "wb") as f:
                        f.write(await resp.read())
                    logging.info(f"Thumbnail downloaded to {output_path}")
                    return True
    except Exception as e:
        logging.error(f"Thumbnail download failed: {e}")

    return False
