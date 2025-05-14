import aiohttp
import asyncio
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import subprocess
import threading
import pymongo
import feedparser
from config import API_ID, API_HASH, BOT_TOKEN, URL_A, START_PIC, MONGO_URI, ADMINS

from webhook import start_webhook

from modules.rss.rss import news_feed_loop


mongo_client = pymongo.MongoClient(MONGO_URI)
db = mongo_client["AnimeNewsBot"]
user_settings_collection = db["user_settings"]
global_settings_collection = db["global_settings"]


app = Client("AnimeNewsBot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


webhook_thread = threading.Thread(target=start_webhook, daemon=True)
webhook_thread.start()


async def escape_markdown_v2(text: str) -> str:
    return text

async def send_message_to_user(chat_id: int, message: str, image_url: str = None):
    try:
        if image_url:
            await app.send_photo(
                chat_id, 
                image_url,
                caption=message,
            )
        else:
            await app.send_message(chat_id, message)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.on_message(filters.command("start"))
async def start(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"

    # Save or update user info in the database
    user_settings_collection.update_one(
        {"_id": user_id},
        {"$set": {
            "username": username,
            "chat_id": chat_id
        }},
        upsert=True
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ᴍᴀɪɴ ʜᴜʙ", url="https://t.me/Bots_Nation"),
            InlineKeyboardButton("ꜱᴜᴩᴩᴏʀᴛ ᴄʜᴀɴɴᴇʟ", url="https://t.me/Bots_Nation_Support"),
        ],
        [
            InlineKeyboardButton("ᴅᴇᴠᴇʟᴏᴩᴇʀ", url="https://t.me/darkxside78"),
        ],
    ])

    photo_url = START_PIC

    await app.send_photo(
        chat_id, 
        photo_url,
        caption=(
            f"**ʙᴀᴋᴋᴀᴀᴀ {username}!!!**\n"
            f"**ɪ ᴀᴍ ᴀɴ ᴀɴɪᴍᴇ ɴᴇᴡs ʙᴏᴛ.**\n"
            f"**ɪ ᴛᴀᴋᴇ ᴀɴɪᴍᴇ ɴᴇᴡs ᴄᴏᴍɪɴɢ ғʀᴏᴍ ʀss ꜰᴇᴇᴅs ᴀɴᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ ᴜᴘʟᴏᴀᴅ ɪᴛ ᴛᴏ ᴍʏ ᴍᴀsᴛᴇʀ's ᴀɴɪᴍᴇ ɴᴇᴡs ᴄʜᴀɴɴᴇʟ.**"
        ),
        reply_markup=buttons
    )

@app.on_message(filters.command("news"))
async def connect_news(client, message):
    chat_id = message.chat.id
    
    if message.from_user.id not in ADMINS:
        await app.send_message(chat_id, "You do not have permission to use this command.")
        return
    if len(message.text.split()) == 1:
        await app.send_message(chat_id, "Please provide a channel id or username (without @).")
        return

    channel = " ".join(message.text.split()[1:]).strip()
    global_settings_collection.update_one({"_id": "config"}, {"$set": {"news_channel": channel}}, upsert=True)
    await app.send_message(chat_id, f"News channel set to: @{channel}")

sent_news_entries = set()

@app.on_message(filters.command("broadcast") & filters.user(ADMINS))
async def broadcast(client, message):
    if len(message.command) < 2:
        await message.reply("Usage: /broadcast Your message here")
        return

    text_to_broadcast = message.text.split(None, 1)[1]

    users = user_settings_collection.find()
    success, fail = 0, 0

    for user in users:
        try:
            await app.send_message(user["chat_id"], text_to_broadcast)
            success += 1
        except Exception as e:
            print(f"Failed to send to {user['chat_id']}: {e}")
            fail += 1

    await message.reply(f"Broadcast complete.\nSuccess: {success}\nFailed: {fail}")

    
async def main():
    await app.start()
    print("Bot is running...")
    asyncio.create_task(news_feed_loop(app, db, global_settings_collection, [URL_A]))
    await asyncio.Event().wait()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
