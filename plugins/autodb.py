import os
import time
import random
import logging
import asyncio
from urllib.parse import urlparse
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import tempfile
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import os
from utils import safe_filename, download_with_aria2c, get_song_download_url_by_spotify_url, download_thumbnail
import random
import asyncio
from info import DUMP_CHANNEL_ID, FAILD_CHAT_ID
from database.db import db
from datetime import datetime 
import pytz
from plugins.jiosavan import search_for_song
import re

logging.basicConfig(level=logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

logger = logging

client_id = "5561376fd0234838863a8c3a6cbb0865"
client_secret = "fa12e995f56c48a28e28fb056e041d18"
auth_manager = SpotifyClientCredentials(client_id=client_id, client_secret=client_secret)
sp = spotipy.Spotify(auth_manager=auth_manager)

song_cache = {}
run_cancel_flags = {}

output_dir = os.path.join(os.getcwd(), "downloads")
os.makedirs(output_dir, exist_ok=True)

@Client.on_message(filters.command("t") & filters.private)
async def show_run_flags(client, message):
    if not run_cancel_flags:
        await message.reply_text("🟢 No running tasks currently.")
        return

    text = "⚙️ **Current run_cancel_flags status:**\n\n"
    for key, val in run_cancel_flags.items():
        text += f"• `{key}` : `{val}`\n"

    await message.reply_text(text)
    

async def extract_track_info(track_id):
    try:
        result = await asyncio.to_thread(sp.track, track_id)
    except Exception as e:
        logging.error(f"Error fetching track info from Spotify API: {e}")
        return None

    title = result['name']

    return title
  
def format_seconds(seconds: int) -> str:
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return ' '.join(parts)





import os
import random
import time
import logging
import pytz
from datetime import datetime
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import asyncio

async def run_batch_from_track_ids(client, track_ids: list, user_id: int, task_id):
    total = len(track_ids)
    sent_count = 0
    extra_sent_count = 0
    failed_tracks = []
    skipped_tracks = []

    key = f"run_{user_id}"
    run_cancel_flags[key] = False

    cancel_keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancel Batch", callback_data=f"cancel_run:{user_id}")]]
    )

    start_time = time.time()
    ist = pytz.timezone('Asia/Kolkata')
    now_ist = datetime.now(ist)
    now_ist_str = now_ist.strftime("%Y-%m-%d %H:%M:%S %z")
    logging.info(f"{now_ist_str}")

    status_msg = await client.send_message(
        user_id,
        f"📂 **Batch Download Started!**\n"
        f"🎵 Total Tracks: **{total}**\n"
        f"✅ Sent (1 per track): **0**\n"
        f"➕ Extra Sends: **0**\n"
        f"⏳ Remaining: **{total}**",
        reply_markup=cancel_keyboard
    )

    await db.tasks_collection.update_one(
        {"_id": task_id},
        {"$set": {
            "status": "running",
            "sent_count": 0,
            "extra_sent_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "updated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %z")
        }}
    )

    for idx, track_id in enumerate(track_ids, 1):
        if run_cancel_flags.get(key):
            end_time = time.time()
            formatted_time = format_seconds(int(end_time - start_time))

            await db.tasks_collection.update_one(
                {"_id": task_id},
                {"$set": {
                    "status": "cancelled",
                    "sent_count": sent_count,
                    "extra_sent_count": extra_sent_count,
                    "skipped_count": len(skipped_tracks),
                    "failed_count": len(failed_tracks),
                    "time_taken": formatted_time,
                    "updated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %z")
                }}
            )

            await status_msg.edit(
                f"❌ Batch cancelled by user.\n"
                f"🎵 Total Tracks: **{total}**\n"
                f"✅ Sent (1 per track): **{sent_count}**\n"
                f"➕ Extra Sends: **{extra_sent_count}**\n"
                f"⏭️ Skipped: **{len(skipped_tracks)}**\n"
                f"❌ Failed: **{len(failed_tracks)}**\n"
                f"⏳ Time Taken: **{formatted_time}**",
                reply_markup=None
            )
            break

        try:
            await status_msg.edit(
                f"⬇️ Processing track {idx} of {total}\n"
                f"✅ Sent (1 per track): {sent_count}\n"
                f"➕ Extra Sends: {extra_sent_count}\n"
                f"⏭️ Skipped: {len(skipped_tracks)}\n"
                f"❌ Failed: {len(failed_tracks)}\n"
                f"⏳ Remaining: {total - sent_count - len(skipped_tracks) - len(failed_tracks)}",
                reply_markup=cancel_keyboard
            )


            title_spotify = await extract_track_info(track_id)
            song_variants = search_for_song(title_spotify, lyrics=False, songdata=True)
        
            if not song_variants:
                failed_tracks.append(track_id)
                continue

            first_variant_done = False
            for variant in song_variants:
                music_id = variant.get("id")
                variant_in_db = await db.get_dump_file_id_by_jio(music_id)
                if variant_in_db:
                    extra_sent_count += 1
                    continue

                song_url = variant.get("media_url")
                song_title = variant.get("song")
                artist = variant.get("primary_artists")
                duration = variant.get("duration")
                thumb_url = variant.get("image")

                base_name = safe_filename(song_title)
                safe_name = f"{base_name}_{random.randint(100, 999)}.mp3"
                download_path = os.path.join(output_dir, safe_name)

                success = await download_with_aria2c(song_url, output_dir, safe_name)
                if not success or not os.path.exists(download_path):
                    logging.error(f"Download failed for {song_url}")
                    continue

                thumb_path = os.path.join(output_dir, safe_filename(song_title) + ".jpg")
                thumb_success = await download_thumbnail(thumb_url, thumb_path) if thumb_url else False

                dump_caption = (
                    f"🆔 Music ID: {music_id or 'N/A'}\n"
                    f"💽 Album: {variant.get('album', 'Unknown')}\n"
                    f"📅 Year: {variant.get('year', 'N/A')}\n"
                    f"⏱ Duration: {duration}\n"
                )
                dump_msg = await client.send_audio(
                    DUMP_CHANNEL_ID,
                    download_path,
                    caption=dump_caption,
                    duration=int(duration or 0),
                    thumb=thumb_path if thumb_success and os.path.exists(thumb_path) else None,
                    title=song_title,
                    performer=artist
                )

                if not first_variant_done:
                    sent_count += 1
                    first_variant_done = True
                else:
                    extra_sent_count += 1

                if os.path.exists(download_path):
                    os.remove(download_path)
                if thumb_success and os.path.exists(thumb_path):
                    os.remove(thumb_path)

                await db.save_dump_file_id_by_jio(music_id, {
                    "file_id": dump_msg.audio.file_id,
                    "song_title": song_title,
                    "artist": artist,
                    "album": variant.get("album"),
                    "year": variant.get("year"),
                    "duration": duration,
                    "thumbnail": thumb_url,
                    "saved_at": datetime.utcnow()
                })

                # Update DB every 2 sends or at end
                if (sent_count + extra_sent_count) % 2 == 0 or idx == total:
                    await db.tasks_collection.update_one(
                        {"_id": task_id},
                        {"$set": {
                            "sent_count": sent_count,
                            "extra_sent_count": extra_sent_count,
                            "skipped_count": len(skipped_tracks),
                            "failed_count": len(failed_tracks),
                            "updated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %z")
                        }}
                    )

                await status_msg.edit(
                    f"⬇️ Processing track {idx} of {total}: **{song_title}**\n"
                    f"✅ Sent (1 per track): {sent_count}\n"
                    f"➕ Extra Sends: {extra_sent_count}\n"
                    f"⏭️ Skipped: {len(skipped_tracks)}\n"
                    f"❌ Failed: {len(failed_tracks)}\n"
                    f"⏳ Remaining: {total - sent_count - len(skipped_tracks) - len(failed_tracks)}",
                    reply_markup=cancel_keyboard
                )
                await asyncio.sleep(1)

        except Exception as e:
            logging.error(f"Error with {track_id}: {e}")
            failed_tracks.append(track_id)

    # Retry logic with same Jio Savan style
    if failed_tracks:
        await asyncio.sleep(10)
        await client.send_message(user_id, f"🔁 Retrying {len(failed_tracks)} failed tracks...")

        retry_success = []
        retry_failed = []

        for idx, track_id in enumerate(failed_tracks, 1):
            if run_cancel_flags.get(key):
                await client.send_message(user_id, "❌ Retry cancelled by user.")
                break

            try:
                # Check DB before retrying
                dump_file_id = await db.get_dump_file_id_by_jio(track_id)
                if dump_file_id:
                    retry_success.append(track_id)
                    continue

                title_spotify = await extract_track_info(track_id)
                song_variants = search_for_song(title_spotify, lyrics=False, songdata=True)
                logging.info(f"Retry search result for '{title_spotify}': {song_variants}")

                if not song_variants:
                    retry_failed.append(track_id)
                    continue

                first_variant_done = False
                for variant in song_variants:
                    music_id = variant.get("id")
                    variant_in_db = await db.get_dump_file_id_by_jio(music_id)
                    if variant_in_db:
                        retry_success.append(track_id)
                        first_variant_done = True
                        break

                    song_url = variant.get("media_url")
                    song_title = variant.get("song")
                    artist = variant.get("primary_artists")
                    duration = variant.get("duration")
                    thumb_url = variant.get("image")

                    base_name = safe_filename(song_title)
                    safe_name = f"{base_name}_{random.randint(100, 999)}.mp3"
                    download_path = os.path.join(output_dir, safe_name)

                    success = await download_with_aria2c(song_url, output_dir, safe_name)
                    if not success or not os.path.exists(download_path):
                        logging.error(f"Retry download failed for {song_url}")
                        continue

                    thumb_path = os.path.join(output_dir, safe_filename(song_title) + ".jpg")
                    thumb_success = await download_thumbnail(thumb_url, thumb_path) if thumb_url else False

                    dump_caption = (
                        f"🆔 Music ID: {music_id or 'N/A'}\n"
                        f"💽 Album: {variant.get('album', 'Unknown')}\n"
                        f"📅 Year: {variant.get('year', 'N/A')}\n"
                        f"⏱ Duration: {duration}\n"
                    )
                    dump_msg = await client.send_audio(
                        DUMP_CHANNEL_ID,
                        download_path,
                        caption=dump_caption,
                        duration=int(duration or 0),
                        thumb=thumb_path if thumb_success and os.path.exists(thumb_path) else None,
                        title=song_title,
                        performer=artist
                    )

                    retry_success.append(track_id)
                    sent_count += 1

                    if os.path.exists(download_path):
                        os.remove(download_path)
                    if thumb_success and os.path.exists(thumb_path):
                        os.remove(thumb_path)

                    await db.save_dump_file_id_by_jio(music_id, {
                        "file_id": dump_msg.audio.file_id,
                        "song_title": song_title,
                        "artist": artist,
                        "album": variant.get("album"),
                        "year": variant.get("year"),
                        "duration": duration,
                        "thumbnail": thumb_url,
                        "saved_at": datetime.utcnow()
                    })

                    first_variant_done = True
                    break

                if not first_variant_done:
                    retry_failed.append(track_id)

            except Exception as e:
                logging.error(f"Retry error for {track_id}: {e}")
                retry_failed.append(track_id)

        await client.send_message(
            user_id,
            f"🔁 Retry complete.\n✅ Recovered: {len(retry_success)}\n❌ Still Failed: {len(retry_failed)}"
        )
        failed_tracks = retry_failed

    if not run_cancel_flags.get(key):
        end_time = time.time()
        formatted_time = format_seconds(int(end_time - start_time))
        await db.tasks_collection.update_one(
            {"_id": task_id},
            {"$set": {
                "status": "done",
                "sent_count": sent_count,
                "extra_sent_count": extra_sent_count,
                "skipped_count": len(skipped_tracks),
                "failed_count": len(failed_tracks),
                "time_taken": formatted_time,
                "updated_at": datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S %z")
            }}
        )

        await status_msg.edit(
            f"✅ **Batch Done!**\n"
            f"🎵 Total: **{total}**\n"
            f"✅ Sent (1 per track): **{sent_count}**\n"
            f"➕ Extra Sends: **{extra_sent_count}**\n"
            f"⏭️ Skipped: **{len(skipped_tracks)}**\n"
            f"❌ Failed: **{len(failed_tracks)}**\n"
            f"⏳ Time Taken: **{formatted_time}**",
            reply_markup=None
        )
        await client.send_message(user_id, "**🔁 Task complete**")

    if failed_tracks:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".txt", mode="w") as tmp_file:
            tmp_file.write("\n".join(failed_tracks))
            failed_file_path = tmp_file.name

        await client.send_document(
            user_id,
            failed_file_path,
            caption=f"⚠️ Final failed tracks: {len(failed_tracks)}"
        )
        await client.send_document(
            FAILD_CHAT_ID,
            failed_file_path,
            caption=f"⚠️ Final failed log after retry for user `{user_id}`."
        )
        os.remove(failed_file_path)

    run_cancel_flags.pop(key, None)


@Client.on_callback_query(filters.regex(r"cancel_run:(\d+)"))
async def cancel_run_batch(client, callback_query):
    user_id = int(callback_query.data.split(":")[1])
    key = f"run_{user_id}"
    run_cancel_flags[key] = True
    await callback_query.answer("✅ Batch cancelled!", show_alert=True)
