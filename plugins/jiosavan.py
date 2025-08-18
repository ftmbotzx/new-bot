import requests, aiohttp
import json
import re
import base64
import logging
import os
import html
from traceback import print_exc
from pyDes import des, ECB, PAD_PKCS5

import aiohttp
import urllib.parse
from pyrogram import Client, filters
from pyrogram.types import Message
# ----------------------

import aiohttp
import logging
import re
import asyncio

import aiohttp
import logging
from pyrogram import Client, filters

async def extract_track_info(track_id: str):
    """
    Fetch track title, author, and thumbnail from Spotify oEmbed.
    Fallback to HTML parsing if oEmbed fails.
    """
    oembed_url = f"https://open.spotify.com/oembed?url=https://open.spotify.com/track/{track_id}"
    track_url = f"https://open.spotify.com/track/{track_id}"

    import re
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(track_url) as resp:
                if resp.status != 200:
                    logging.error(f"Track page fetch failed: {resp.status}")
                    return None
                html = await resp.text()
                match = re.search(r"<title>(.*?) - .*? \| Spotify</title>", html)
                if match:
                    return {
                        "title": match.group(1).strip()
                    }
    except Exception as e:
        logging.error(f"Fallback HTML parse error for {track_id}: {e}")
    
    return None



# --- test ---
# asyncio.run(extract_track_info("59F97An4YiBFXasHrncXgE"))


# Endpoints
# ----------------------
search_base_url = "https://www.jiosaavn.com/api.php?__call=autocomplete.get&_format=json&_marker=0&cc=in&includeMetaTags=1&query="
song_details_base_url = "https://www.jiosaavn.com/api.php?__call=song.getDetails&cc=in&_marker=0%3F_marker%3D0&_format=json&pids="
album_details_base_url = "https://www.jiosaavn.com/api.php?__call=content.getAlbumDetails&_format=json&cc=in&_marker=0%3F_marker%3D0&albumid="
playlist_details_base_url = "https://www.jiosaavn.com/api.php?__call=playlist.getDetails&_format=json&cc=in&_marker=0%3F_marker%3D0&listid="
lyrics_base_url = "https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&ctx=web6dot0&api_version=4&_format=json&_marker=0%3F_marker%3D0&lyrics_id="

# ----------------------
# JSON helpers (fix “From "XYZ"”, ZWJ, bad commas, BOM etc.)
# ----------------------
_INVISIBLE = "\u200b\u200c\u200d\u2060\u2028\u2029"

def _fix_autocomplete_weird_quotes(text: str) -> str:
    # (From "Movie") -> (From 'Movie')
    return re.sub(r'\(From "([^"]+)"\)', r"(From '\1')", text)

def _strip_invisible(text: str) -> str:
    return text.translate({ord(c): None for c in _INVISIBLE})

def _strip_bom(text: str) -> str:
    return text.lstrip("\ufeff")

def _strip_trailing_commas(text: str) -> str:
    # Remove trailing commas before } or ]
    text = re.sub(r',(\s*[}\]])', r'\1', text)
    return text

def safe_json_loads(text: str):
    fixed = _strip_bom(text)
    fixed = _strip_invisible(fixed)
    fixed = _fix_autocomplete_weird_quotes(fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        fixed2 = _strip_trailing_commas(fixed)
        return json.loads(fixed2)

def request_json(url: str, timeout: int = 15):
    resp = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
    # First try built-in json parser (fast path)
    try:
        return resp.json()
    except Exception:
        return safe_json_loads(resp.text)

# ----------------------
# Cleaners
# ----------------------
def clean_string(s: str) -> str:
    if not s:
        return ""
    # Handle HTML entities and common cases
    s = html.unescape(s)
    return s.replace("&quot;", "'").replace("&amp;", "&").replace("&#039;", "'")

def decrypt_url(url):
    try:
        des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0", pad=None, padmode=PAD_PKCS5)
        enc_url = base64.b64decode(url.strip())
        dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
        dec_url = dec_url.replace("_96.mp4", "_320.mp4")
        return dec_url
    except Exception:
        return None

# ----------------------
# Search / IDs
# ----------------------
def search_for_song(query, lyrics=False, songdata=True):
    if query.startswith('http') and 'saavn.com' in query:
        sid = get_song_id(query)
        return get_song(sid, lyrics)

    q = urllib.parse.quote_plus(query)
    url = search_base_url + q
    response = request_json(url)

    song_response = (response.get('songs') or {}).get('data', []) if isinstance(response, dict) else []
    if not songdata:
        return song_response

    songs = []
    for song in song_response:
        sid = song.get('id')
        if not sid:
            continue
        song_data = get_song(sid, lyrics)
        if song_data:
            songs.append(song_data)
    return songs

def get_song(id, lyrics=False):
    try:
        url = song_details_base_url + id
        song_response = request_json(url)
        payload = song_response.get(id, {}) if isinstance(song_response, dict) else {}
        song_data = format_song(payload, lyrics)
        if song_data:
            return song_data
    except Exception:
        print_exc()
    return None

def get_song_id(url):
    # Try to fetch pid or fallback to embedded ids
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    txt = res.text
    try:
        return txt.split('"pid":"')[1].split('"')[0]
    except Exception:
        try:
            return txt.split('"song":{"type":"')[1].split('","image":')[0].split('"id":"')[-1]
        except Exception:
            return None

def get_album(album_id, lyrics=False):
    try:
        data = request_json(album_details_base_url + album_id)
        return format_album(data, lyrics)
    except Exception:
        print_exc()
        return None

def get_album_id(input_url_or_query: str):
    # If URL -> try HTML scrape as before
    if input_url_or_query.startswith("http"):
        res = requests.get(input_url_or_query, headers={"User-Agent": "Mozilla/5.0"})
        txt = res.text
        try:
            return txt.split('"album_id":"')[1].split('"')[0]
        except IndexError:
            try:
                return txt.split('"page_id","')[1].split('","')[0]
            except Exception:
                return None
    # Else treat as search query: prefer album hit, else first song's albumid
    try:
        q = urllib.parse.quote_plus(input_url_or_query)
        resp = request_json(search_base_url + q)
        albums = (resp.get('albums') or {}).get('data', []) if isinstance(resp, dict) else []
        if albums:
            # direct album id
            aid = albums[0].get('id') or albums[0].get('albumid')
            if aid:
                return str(aid)
        songs = (resp.get('songs') or {}).get('data', [])
        if songs:
            return str(songs[0].get('albumid') or songs[0].get('album_id') or "")
    except Exception:
        print_exc()
    return None

def get_playlist(listId, lyrics=False):
    try:
        data = request_json(playlist_details_base_url + listId)
        return format_playlist(data, lyrics)
    except Exception:
        print_exc()
        return None

def get_playlist_id(input_url):
    res = requests.get(input_url, headers={"User-Agent": "Mozilla/5.0"}).text
    try:
        return res.split('"type":"playlist","id":"')[1].split('"')[0]
    except IndexError:
        try:
            return res.split('"page_id","')[1].split('","')[0]
        except Exception:
            return None

def get_lyrics(id):
    data = request_json(lyrics_base_url + id)
    return (data or {}).get('lyrics')

# ----------------------
# Formatters
# ----------------------
def format_song(data, lyrics=False):
    if not data:
        return {}

    # Prefer decrypted URL when not DRM, else use media_url / preview fallback
    media_url = None
    if str(data.get('is_drm', 0)) in ("1", 1, "true"):
        media_url = data.get('media_url')  # DRM: don't try to decrypt
    else:
        media_url = decrypt_url(data.get('encrypted_media_url', '') or '') or data.get('media_url')

    if media_url:
        if data.get('320kbps') != "true":
            media_url = media_url.replace("_320.mp4", "_160.mp4")
        preview_url = media_url.replace("_320.mp4", "_96_p.mp4").replace("_160.mp4", "_96_p.mp4").replace("//aac.", "//preview.")
    else:
        # last resort from preview
        url = (data.get('media_preview_url') or '').replace("preview", "aac")
        if data.get('320kbps') == "true":
            url = url.replace("_96_p.mp4", "_320.mp4")
        else:
            url = url.replace("_96_p.mp4", "_160.mp4")
        media_url = url
        preview_url = (data.get('media_preview_url') or '')

    data['media_url'] = media_url
    data['media_preview_url'] = preview_url

    data['song'] = clean_string(data.get('song', 'Unknown'))
    data['singers'] = clean_string(data.get('singers', 'Unknown'))
    data['starring'] = clean_string(data.get('starring', ''))
    data['album'] = clean_string(data.get('album', 'Unknown'))
    data['primary_artists'] = clean_string(data.get('primary_artists', 'Unknown Artist'))
    data['image'] = (data.get('image') or '').replace("150x150", "500x500")
    data['language'] = data.get('language', 'Unknown')


    if lyrics:
        if str(data.get('has_lyrics', 'false')).lower() == 'true':
            data['lyrics'] = get_lyrics(data.get('id'))
        else:
            data['lyrics'] = None

    if 'copyright_text' in data and isinstance(data['copyright_text'], str):
        data['copyright_text'] = data['copyright_text'].replace("&copy;", "©")

    return data

def format_album(data, lyrics=False):
    if not data:
        return {}
    data['image'] = (data.get('image') or '').replace("150x150", "500x500")
    data['name'] = clean_string(data.get('name', ''))
    data['primary_artists'] = clean_string(data.get('primary_artists', ''))
    data['title'] = clean_string(data.get('title', ''))

    songs = data.get('songs', []) or []
    out = []
    for song in songs:
        out.append(format_song(song, lyrics))
    data['songs'] = out
    return data

def format_playlist(data, lyrics=False):
    if not data:
        return {}

    data['firstname'] = clean_string(data.get('firstname', ''))
    data['listname'] = clean_string(data.get('listname', ''))
    songs = data.get('songs', []) or []
    out = []
    for song in songs:
        out.append(format_song(song, lyrics))
    data['songs'] = out
    return data

# ----------------------
# Download
# ----------------------
async def download_file(url, path):
    if not url:
        logging.error(f"Empty URL for download: {path}")
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=120)
        headers = {"User-Agent": "Mozilla/5.0"}
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    with open(path, 'wb') as f:
                        f.write(await resp.read())
                    return path
                else:
                    logging.error(f"Download failed with status {resp.status} for URL {url}")
    except Exception as e:
        logging.error(f"Error downloading file: {e}")
    return None

# ----------------------
# Pyrogram command
# ----------------------
from pyrogram import Client, filters
import aiohttp

@Client.on_message(filters.command("dl"))
async def download_song_info(client, message):
    if len(message.command) < 2:
        return await message.reply("❌ Usage: `/dl <spotify_track_id>`")
    
    track_id = message.command[1].strip()

    track_info = await extract_track_info(track_id)
    if not track_info:
        return await message.reply("⚠️ Failed to fetch track info.")

    title = track_info.get("title", "Unknown Title")

    caption = f"🎵 **{title}**\n"
    await message.reply(caption)
