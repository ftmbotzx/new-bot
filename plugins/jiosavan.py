import requests
import json
import re
from traceback import print_exc
import base64
from pyDes import des, ECB, PAD_PKCS5

import aiohttp
import urllib.parse
import logging
import json
import os
from pyrogram import Client, filters
from pyrogram.types import Message


# Endpoints you provided earlier — set these properly in your endpoints.py or define here
search_base_url = "https://www.jiosaavn.com/api.php?__call=autocomplete.get&_format=json&_marker=0&cc=in&includeMetaTags=1&query="
song_details_base_url = "https://www.jiosaavn.com/api.php?__call=song.getDetails&cc=in&_marker=0%3F_marker%3D0&_format=json&pids="
album_details_base_url = "https://www.jiosaavn.com/api.php?__call=content.getAlbumDetails&_format=json&cc=in&_marker=0%3F_marker%3D0&albumid="
playlist_details_base_url = "https://www.jiosaavn.com/api.php?__call=playlist.getDetails&_format=json&cc=in&_marker=0%3F_marker%3D0&listid="
lyrics_base_url = "https://www.jiosaavn.com/api.php?__call=lyrics.getLyrics&ctx=web6dot0&api_version=4&_format=json&_marker=0%3F_marker%3D0&lyrics_id="


def search_for_song(query, lyrics=False, songdata=True):
    if query.startswith('http') and 'saavn.com' in query:
        id = get_song_id(query)
        return get_song(id, lyrics)

    url = search_base_url + query
    response = requests.get(url).text.encode().decode('unicode-escape')
    pattern = r'\(From "([^"]+)"\)'
    response = json.loads(re.sub(pattern, r"(From '\1')", response))
    song_response = response.get('songs', {}).get('data', [])
    if not songdata:
        return song_response
    songs = []
    for song in song_response:
        id = song['id']
        song_data = get_song(id, lyrics)
        if song_data:
            songs.append(song_data)
    return songs


def get_song(id, lyrics=False):
    try:
        url = song_details_base_url + id
        song_response = requests.get(url).text.encode().decode('unicode-escape')
        song_response = json.loads(song_response)
        song_data = format_song(song_response.get(id, {}), lyrics)
        if song_data:
            return song_data
    except Exception:
        print_exc()
        return None


def get_song_id(url):
    res = requests.get(url, data=[('bitrate', '320')])
    try:
        return res.text.split('"pid":"')[1].split('","')[0]
    except IndexError:
        return res.text.split('"song":{"type":"')[1].split('","image":')[0].split('"id":"')[-1]


def get_album(album_id, lyrics=False):
    try:
        response = requests.get(album_details_base_url + album_id)
        if response.status_code == 200:
            songs_json = response.text.encode().decode('unicode-escape')
            songs_json = json.loads(songs_json)
            return format_album(songs_json, lyrics)
    except Exception:
        print_exc()
        return None


def get_album_id(input_url):
    res = requests.get(input_url)
    try:
        return res.text.split('"album_id":"')[1].split('"')[0]
    except IndexError:
        return res.text.split('"page_id","')[1].split('","')[0]


def get_playlist(listId, lyrics=False):
    try:
        response = requests.get(playlist_details_base_url + listId)
        if response.status_code == 200:
            songs_json = response.text.encode().decode('unicode-escape')
            songs_json = json.loads(songs_json)
            return format_playlist(songs_json, lyrics)
        return None
    except Exception:
        print_exc()
        return None


def get_playlist_id(input_url):
    res = requests.get(input_url).text
    try:
        return res.split('"type":"playlist","id":"')[1].split('"')[0]
    except IndexError:
        return res.split('"page_id","')[1].split('","')[0]


def get_lyrics(id):
    url = lyrics_base_url + id
    lyrics_json = requests.get(url).text
    lyrics_text = json.loads(lyrics_json)
    return lyrics_text.get('lyrics')


def format_song(data, lyrics=False):
    if not data:
        return {}

    try:
        data['media_url'] = decrypt_url(data['encrypted_media_url'])
        if data.get('320kbps') != "true":
            data['media_url'] = data['media_url'].replace("_320.mp4", "_160.mp4")
        data['media_preview_url'] = data['media_url'].replace("_320.mp4", "_96_p.mp4").replace("_160.mp4", "_96_p.mp4").replace("//aac.", "//preview.")
    except (KeyError, TypeError):
        url = data.get('media_preview_url', '')
        url = url.replace("preview", "aac")
        if data.get('320kbps') == "true":
            url = url.replace("_96_p.mp4", "_320.mp4")
        else:
            url = url.replace("_96_p.mp4", "_160.mp4")
        data['media_url'] = url

    data['song'] = clean_string(data.get('song', 'Unknown'))
    data['singers'] = clean_string(data.get('singers', 'Unknown'))
    data['starring'] = clean_string(data.get('starring', ''))
    data['album'] = clean_string(data.get('album', 'Unknown'))
    data["primary_artists"] = clean_string(data.get("primary_artists", "Unknown Artist"))
    data['image'] = data.get('image', '').replace("150x150", "500x500")
    data['language'] = data.get('language', 'Unknown')

    if lyrics:
        if data.get('has_lyrics') == 'true':
            data['lyrics'] = get_lyrics(data.get('id'))
        else:
            data['lyrics'] = None

    try:
        data['copyright_text'] = data.get('copyright_text', '').replace("&copy;", "©")
    except KeyError:
        pass
    return data


def format_album(data, lyrics=False):
    if not data:
        return {}

    data['image'] = data.get('image', '').replace("150x150", "500x500")
    data['name'] = clean_string(data.get('name', ''))
    data['primary_artists'] = clean_string(data.get('primary_artists', ''))
    data['title'] = clean_string(data.get('title', ''))
    for idx, song in enumerate(data.get('songs', [])):
        data['songs'][idx] = format_song(song, lyrics)
    return data


def format_playlist(data, lyrics=False):
    if not data:
        return {}

    data['firstname'] = clean_string(data.get('firstname', ''))
    data['listname'] = clean_string(data.get('listname', ''))
    for idx, song in enumerate(data.get('songs', [])):
        data['songs'][idx] = format_song(song, lyrics)
    return data


def clean_string(string):
    if not string:
        return ''
    return string.encode().decode().replace("&quot;", "'").replace("&amp;", "&").replace("&#039;", "'")


def decrypt_url(url):
    des_cipher = des(b"38346591", ECB, b"\0\0\0\0\0\0\0\0",
                     pad=None, padmode=PAD_PKCS5)
    enc_url = base64.b64decode(url.strip())
    dec_url = des_cipher.decrypt(enc_url, padmode=PAD_PKCS5).decode('utf-8')
    dec_url = dec_url.replace("_96.mp4", "_320.mp4")
    return dec_url


async def download_file(url, path):
    if not url:
        logging.error(f"Empty URL for download: {path}")
        return None
    try:
        async with aiohttp.ClientSession() as session:
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

@Client.on_message(filters.command("dl") & filters.private)
async def cmd_dl(client: Client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Usage: `/dl song name`", quote=True)

    query = " ".join(message.command[1:])
    await message.reply_text(f"🔍 Searching for **{query}**...", quote=True)

    # Use your defined search function here (sync)
    songs = search_for_song(query, lyrics=False, songdata=True)
    if not songs:
        return await message.reply_text("❌ No results found.", quote=True)

    for song in songs:
        try:
            safe_title = "".join(c for c in song.get('song', 'Unknown') if c.isalnum() or c in " _-").strip()
            filepath = f"/tmp/{safe_title}.mp3"

            downloaded = await download_file(song.get('media_url'), filepath)
            if not downloaded:
                await message.reply_text(f"❌ Could not download {song.get('song', 'Unknown')}")
                continue

            caption = f"🎵 **{song.get('song', 'Unknown')}**\n👤 {song.get('primary_artists', 'Unknown')}\n⏱ {song.get('duration', '0')} sec"
            if song.get('image'):
                await message.reply_photo(photo=song['image'], caption=caption)
            await message.reply_audio(
                audio=filepath,
                title=song.get('song', 'Unknown'),
                performer=song.get('primary_artists', 'Unknown'),
                duration=int(song['duration']) if song.get('duration', '0').isdigit() else None,
                thumb=song.get('image')
            )

            os.remove(filepath)
        except Exception as e:
            logging.error(f"Error sending song: {e}")
