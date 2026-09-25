import os
import re
import logging
import asyncio
import requests
import yt_dlp
import json
import time
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, constants, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "8890075234:AAGrwHpwOeatL0vNi7A0RxzJGODvCPwiZjg"
ADMIN_USERNAME = "@vskmm2"
CHANNEL_LINK = "https://t.me/Monkey_D_Luffykh"
WELCOME_BANNER = "https://i.supaimg.com/2c2963a3-a72b-47fd-ba30-ac78827d2091/5138d4bd-41fe-4c79-9c0f-8b3ca4163b1b.jpg"

VIDKRAKEN_API_KEY = "ed47818e-e446-4d4b-9a82-c91ea8f40a42"
REMOVE_BG_API_KEY = "pxDaKTSYmVmewaADuhXjiVxy"

MEATIKA_API_URL = "https://api.meatika.dev/v1/tts"
MEATIKA_API_KEY = "ck_live_mgGgsfln4gaKHFqid2Lsr7aWes7eI0Pa"

DATA_FILE = "bot_database.json"
WEEK_IN_SECONDS = 7 * 24 * 60 * 60

if not os.path.exists('downloads'):
    os.makedirs('downloads')

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {"users": {}}
        except Exception as e:
            logging.error(f"Error loading JSON database: {e}")
            return {"users": {}}
    return {"users": {}}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving JSON database: {e}")

def check_and_update_user_keys(user_id):
    db = load_data()
    user_id = str(user_id)
    current_time = time.time()

    if "users" not in db:
        db["users"] = {}

    if "keys" in db and isinstance(db["keys"], dict):
        for uid, k_val in db["keys"].items():
            if uid not in db["users"]:
                db["users"][uid] = {"keys": k_val, "last_reset": current_time}
        del db["keys"]

    if user_id not in db["users"]:
        db["users"][user_id] = {"keys": 10, "last_reset": current_time}
        save_data(db)
        return db["users"][user_id]["keys"]

    user_info = db["users"][user_id]
    if not isinstance(user_info, dict):
        user_info = {"keys": 10, "last_reset": current_time}
        db["users"][user_id] = user_info

    last_reset = user_info.get("last_reset", current_time)

    if current_time - last_reset >= WEEK_IN_SECONDS:
        user_info["keys"] = user_info.get("keys", 0) + 10
        user_info["last_reset"] = current_time
        save_data(db)

    return user_info.get("keys", 0)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

def get_main_reply_keyboard():
    keyboard = [
        [KeyboardButton("📥 ទាញយកវីដេអូ/MP3"), KeyboardButton("✂️ លុប BG")],
        [KeyboardButton("🌐 បង្កើត Xray VPN"), KeyboardButton("🗣️ បម្លែងសំឡេង (TTS)")],
        [KeyboardButton("🌐 បកប្រែភាសា"), KeyboardButton("🚀 បន្ថែម View/Like")],
        [KeyboardButton("📢 ចូលរួម Channel"), KeyboardButton("💬 ទំនាក់ទំនង Admin")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def ensure_user_data(context):
    if not isinstance(context.user_data, dict):
        context.user_data = {}

def download_media_file(url: str, is_mp3: bool = False):
    """
    វិធីសាស្ត្រទាញយក Media ដែលបានកែសម្រួលដើម្បីដោះស្រាយបញ្ហា YouTube Error
    """
    file_extension = "mp3" if is_mp3 else "mp4"
    output_filename = f"downloads/media_{int(time.time())}.{file_extension}"

    # --- វិធីសាស្ត្រទី ១: ប្រើប្រាស់ yt-dlp ជាមួយ Configuration ប្រឆាំងការ Block ---
    ydl_opts = {
        'outtmpl': output_filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
            }
        }
    }

    if is_mp3:
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # ជ្រើសរើស Format MP4 ដែលមានទាំងរូបភាព និងសំឡេង (កម្រិតច្បាស់ល្មម)
        ydl_opts.update({'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4]/best'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Downloaded Media')
            
            # ឆែកមើលក្រែងលោឈ្មោះ File ត្រូវបានប្តូរដោយ yt-dlp
            if not os.path.exists(output_filename):
                downloaded_file = ydl.prepare_filename(info)
                if is_mp3:
                    downloaded_file = os.path.splitext(downloaded_file)[0] + ".mp3"
                if os.path.exists(downloaded_file):
                    return downloaded_file, title, url
            else:
                return output_filename, title, url
    except Exception as e:
        logging.error(f"yt-dlp Primary Error: {e}")

    # --- វិធីសាស្ត្រទី ២: Fallback ទៅកាន់ Cobalt API (ប្រសិនបើ yt-dlp បរាជ័យ) ---
    try:
        cobalt_url = "https://api.cobalt.tools/api/json"
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "isAudioOnly": is_mp3,
            "aFormat": "mp3" if is_mp3 else "best"
        }
        res = requests.post(cobalt_url, headers=headers, json=payload, timeout=15)
        if res.status_code == 200:
            data = res.json()
            dl_url = data.get("url")
            if dl_url:
                file_req = requests.get(dl_url, stream=True, timeout=60)
                with open(output_filename, 'wb') as f:
                    for chunk in file_req.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                return output_filename, "Downloaded Media", dl_url
    except Exception as e:
        logging.error(f"Cobalt API Fallback Error: {e}")

    # --- វិធីសាស្ត្រទី ៣: Fallback ទៅ VidKraken API ---
    try:
        format_type = "mp3" if is_mp3 else "360"
        submit_url = "https://vidkraken.com/api/v2/download"
        headers = {
            "Authorization": f"Bearer {VIDKRAKEN_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"url": url, "format": format_type}
        
        res = requests.post(submit_url, headers=headers, json=payload, timeout=20)
        data = res.json()
        job_id = data.get("jobId")
        if job_id:
            status_url = f"https://vidkraken.com/api/v2/download/{job_id}"
            for _ in range(15):
                time.sleep(2)
                status_res = requests.get(status_url, headers=headers, timeout=10)
                status_data = status_res.json()
                if status_data.get("status") == "COMPLETED":
                    download_link = status_data.get("downloadUrl")
                    title = status_data.get("title", "YouTube Video")
                    file_req = requests.get(download_link, stream=True, timeout=60)
                    with open(output_filename, 'wb') as f:
                        for chunk in file_req.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                    return output_filename, title, download_link
                elif status_data.get("status") == "FAILED":
                    break
    except Exception as e:
        logging.error(f"VidKraken Fallback Error: {e}")

    return None, None, None

def remove_background(image_path: str) -> str:
    try:
        output_path = image_path.replace(".", "_nobg.")
        with open(image_path, 'rb') as f:
            response = requests.post(
                'https://api.remove.bg/v1.0/removebg',
                files={'image_file': f},
                data={'size': 'auto', 'format': 'png'},
                headers={'X-Api-Key': REMOVE_BG_API_KEY}
            )
        if response.status_code == requests.codes.ok:
            with open(output_path, 'wb') as out:
                out.write(response.content)
            return output_path
    except Exception as e:
        logging.error(f"Remove BG Error: {e}")
    return None

def generate_google_tts(text: str, user_id: str, is_fast: bool = False) -> str:
    try:
        speed_param = "&ttsspeed=1" if is_fast else ""
        encoded_text = requests.utils.quote(text)
        voice_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded_text}&tl=km&client=tw-ob{speed_param}"
        
        res = requests.get(voice_url, timeout=15)
        if res.status_code == 200:
            audio_path = f"downloads/gvoice_{user_id}_{int(time.time())}.mp3"
            with open(audio_path, "wb") as f:
                f.write(res.content)
            return audio_path
    except Exception as e:
        logging.error(f"Google TTS Error: {e}")
    return None

async def set_bot_commands(application):
    commands = [
        BotCommand("start", "ចាប់ផ្តើមប្រើប្រាស់ Bot"),
        BotCommand("removebg", "មុខងារលុបផ្ទៃខាងក្រោយរូបភាព"),
        BotCommand("boost", "បន្ថែម View & Like (TikTok/YT)"),
        BotCommand("tts", "បម្លែងអក្សរទៅជាសំឡេង Voice"),
        BotCommand("translate", "បកប្រែភាសា"),
        BotCommand("help", "របៀបប្រើប្រាស់ Bot")
    ]
    await application.bot.set_my_commands(commands)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ensure_user_data(context)
        context.user_data.clear()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        user_id = update.message.from_user.id
        check_and_update_user_keys(user_id)
        
        welcome_text = (
            "👋 **ស្វាគមន៍មកកាន់ All-in-One Multi-Bot!**\n\n"
            "✨ **មុខងារពិសេស:**\n"
            "📥 ទាញយកវីដេអូ/MP3\n"
            "✂️ លុបផ្ទៃខាងក្រោយរូបភាព (Remove BG)\n"
            "🌐 បង្កើត Xray VPN (Free 10 Key រៀងរាល់ ១ សប្ដាហ៍)\n"
            "🗣️ បម្លែងអក្សរទៅជាសំឡេង Voice Note (មានសំឡេង Loveណាចា & Google Voice)\n"
            "🌐 បកប្រែភាសា និងសេវាកម្មផ្សេងៗ\n\n"
            "👇 **សូមចុចលើប៊ូតុងម៉ឺនុយខាងក្រោម ឬប្រើប្រាស់ Command ក្នុង Menu ដើម្បីចាប់ផ្តើម៖**"
        )

        try:
            await update.message.reply_photo(
                photo=WELCOME_BANNER,
                caption=welcome_text,
                reply_markup=get_main_reply_keyboard(),
                parse_mode="Markdown"
            )
        except Exception:
            await update.message.reply_text(welcome_text, reply_markup=get_main_reply_keyboard(), parse_mode="Markdown")
    except Exception as e:
        logging.error(f"Start command error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "📖 **របៀបប្រើប្រាស់ Bot:**\n\n"
        "1. **📥 ទាញយកវីដេអូ/MP3:** គ្រាន់តែផ្ញើ Link (TikTok, YouTube, FB...) មកកាន់ Bot ផ្ទាល់។\n"
        "2. **✂️ លុប BG:** ប្រើប្រាស់ Command `/removebg` រួចផ្ញើរូបភាពមក។\n"
        "3. **🌐 បង្កើត Xray VPN:** ចុចប៊ូតុង VPN ដើម្បីបង្កើត Config ឥតគិតថ្លៃ។\n"
        "4. **🗣️ បម្លែងសំឡេង:** ប្រើប្រាស់ Command `/tts` ដើម្បីជ្រើសរើសសំឡេង។\n"
        "5. **🌐 បកប្រែភាសា:** ប្រើប្រាស់ Command `/translate` ដើម្បីបកប្រែអត្ថបទ।"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown", reply_markup=get_main_reply_keyboard())

async def removebg_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['mode'] = 'remove_bg'
    await update.message.reply_text("✂️ **ទម្រង់លុបផ្ទៃខាងក្រោយ៖**\nសូមផ្ញើរូបភាពរបស់អ្នកមកទីនេះ Bot នឹងលុប BG ជូនជាទម្រង់ PNG ថ្លា!", parse_mode="Markdown")

async def boost_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    boost_kb = [
        [InlineKeyboardButton("❤️ Like TikTok", callback_data="boost_tiktok_like"), InlineKeyboardButton("👁️ View TikTok", callback_data="boost_tiktok_view")],
        [InlineKeyboardButton("▶️ View YouTube", callback_data="boost_yt_view"), InlineKeyboardButton("👍 Like YouTube", callback_data="boost_yt_like")]
    ]
    await update.message.reply_text("🚀 **សូមជ្រើសរើសសេវាកម្មបន្ថែម View/Like៖**", reply_markup=InlineKeyboardMarkup(boost_kb), parse_mode="Markdown")

async def tts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    tts_kb = [
        [InlineKeyboardButton("🌸 សំឡេង Loveណាចា", callback_data="tts_Loveណាចា")],
        [InlineKeyboardButton("👩 សំឡេងស្រី (ធម្មតា)", callback_data="tts_ស្រី_ធម្មតា"), InlineKeyboardButton("👩 សំឡេងស្រី (លឿន)", callback_data="tts_ស្រី_លឿន")],
        [InlineKeyboardButton("👨 សំឡេងប្រុស (ធម្មតា)", callback_data="tts_ប្រុស_ធម្មតា"), InlineKeyboardButton("👨 សំឡេងប្រុស (លឿន)", callback_data="tts_ប្រុស_លឿន")]
    ]
    await update.message.reply_text("🗣️ **សូមជ្រើសរើសប្រភេទសំឡេងដែលអ្នកចង់បាន៖**", reply_markup=InlineKeyboardMarkup(tts_kb), parse_mode="Markdown")

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    trans_keyboard = [
        [InlineKeyboardButton("🇰🇭 ខ្មែរ ➔ 🇬🇧 អង់គ្លេស", callback_data="set_tr_km_en"), InlineKeyboardButton("🇬🇧 អង់គ្លេស ➔ 🇰🇭 ខ្មែរ", callback_data="set_tr_en_km")],
        [InlineKeyboardButton("🇰🇭 ខ្មែរ ➔ 🇨🇳 ចិន", callback_data="set_tr_km_zh-CN"), InlineKeyboardButton("🇨🇳 ចិន ➔ 🇰🇭 ខ្មែរ", callback_data="set_tr_zh-CN_km")]
    ]
    await update.message.reply_text("🌐 **សូមជ្រើសរើសទិសដៅនៃការបកប្រែ៖**", reply_markup=InlineKeyboardMarkup(trans_keyboard), parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ensure_user_data(context)

    if data in ["dl_mp4", "dl_mp3"]:
        target_url = context.user_data.get('download_url')
        if not target_url:
            await query.message.reply_text("❌ រកមិនឃើញ Link ឡើយ! សូមផ្ញើ Link ម្ដងទៀត។")
            return

        is_mp3 = (data == "dl_mp3")
        status_msg = await query.message.reply_text("⏳ កំពុងដំណើរការទាញយក File... សូមរង់ចាំបន្តិច!")
        
        action = constants.ChatAction.UPLOAD_VOICE if is_mp3 else constants.ChatAction.UPLOAD_VIDEO
        await context.bot.send_chat_action(chat_id=query.message.chat_id, action=action)

        loop = asyncio.get_event_loop()
        file_path, title, direct_url = await loop.run_in_executor(None, download_media_file, target_url, is_mp3)

        if file_path and os.path.exists(file_path):
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
            caption = f"✅ **ទាញយកជោគជ័យ!**\n📌 {title if title else ''}"
            try:
                if file_size_mb > 48:
                    await query.message.reply_text(f"⚠️ File មានទំហំធំពេក (>50MB)\n🔗 Download ផ្ទាល់៖ {direct_url}")
                else:
                    await context.bot.send_chat_action(chat_id=query.message.chat_id, action=action)
                    with open(file_path, 'rb') as file:
                        if is_mp3:
                            await query.message.reply_audio(audio=file, caption=caption, parse_mode="Markdown")
                        else:
                            await query.message.reply_video(video=file, caption=caption, parse_mode="Markdown")
            finally:
                if os.path.exists(file_path):
                    os.remove(file_path)
        else:
            await query.message.reply_text("❌ មិនអាចទាញយក Media ពី Link នេះបានទេ! (សូមព្យាយាម Link ផ្សេង ឬប្តូរម្តងទៀត)")

        try:
            await context.bot.delete_message(chat_id=status_msg.chat_id, message_id=status_msg.message_id)
        except Exception:
            pass

    elif data.startswith("vpn_srv_"):
        server_choice = data.replace("vpn_srv_", "")
        context.user_data['vpn_server'] = server_choice
        context.user_data['mode'] = 'vpn_enter_name'
        
        await query.message.reply_text(
            f"🌍 Server បានជ្រើសរើស៖ **{server_choice}** (500 GB / ៣០ ថ្ងៃ)\n\n"
            f"✏️ **សូមវាយបញ្ចូលឈ្មោះ (Username) របស់អ្នកសម្រាប់បង្កើត Xray VPN៖**",
            parse_mode="Markdown"
        )

    elif data.startswith("tts_"):
        context.user_data['tts_mode'] = data
        context.user_data['mode'] = 'tts'
        mode_name = data.replace("tts_", "").replace("_", " ")
        await query.message.reply_text(f"✅ បានជ្រើសរើសសំឡេង៖ **{mode_name}**\n\nសូមផ្ញើសារ ឬអក្សរដែលអ្នកចង់ឱ្យវាបម្លែងជា Voice Note មកទីនេះ៖", parse_mode="Markdown")

    elif data.startswith("set_tr_"):
        mode = data.replace("set_tr_", "")
        context.user_data['trans_mode'] = mode
        context.user_data['mode'] = 'translate'
        await query.message.reply_text("✅ បានកំណត់ជោគជ័យ! សូមផ្ញើសារ/អក្សរដែលអ្នកចង់បកប្រែមកទីនេះ៖")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ensure_user_data(context)
    if context.user_data.get('mode') == 'remove_bg':
        status_msg = await update.message.reply_text("✂️ កំពុងលុបផ្ទៃខាងក្រោយ និងបង្កើតរូបភាព PNG... សូមរង់ចាំបន្តិច!")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.UPLOAD_PHOTO)
        
        photo_file = await update.message.photo[-1].get_file()
        input_path = f"downloads/{update.message.from_user.id}_{int(time.time())}.jpg"
        await photo_file.download_to_drive(input_path)

        loop = asyncio.get_event_loop()
        output_path = await loop.run_in_executor(None, remove_background, input_path)

        if output_path and os.path.exists(output_path):
            await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f, 
                    filename="removed_background.png",
                    caption="✨ **លុបផ្ទៃខាងក្រោយជោគជ័យ (PNG Format ថ្លា)!**", 
                    parse_mode="Markdown"
                )
            if os.path.exists(output_path):
                os.remove(output_path)
        else:
            await update.message.reply_text("❌ មិនអាចលុបផ្ទៃខាងក្រោយបានទេ!")

        if os.path.exists(input_path):
            os.remove(input_path)
        context.user_data.clear()
        try:
            await context.bot.delete_message(chat_id=status_msg.chat_id, message_id=status_msg.message_id)
        except Exception:
            pass
    else:
        await update.message.reply_text("📸 សូមចុចប៊ូតុង '✂️ លុប BG' ឬប្រើប្រាស់ `/removebg` ជាមុនសិន មុននឹងផ្ញើរូបភាពមក!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return
        
    ensure_user_data(context)
    user = update.message.from_user
    user_id = str(user.id)
    username = f"@{user.username}" if user.username else "គ្មាន (No Username)"

    # --- 1. ប៊ូតុងម៉ឺនុយមេ ---
    if text == "📥 ទាញយកវីដេអូ/MP3":
        context.user_data.clear()
        context.user_data['mode'] = 'download'
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        await update.message.reply_text("📥 **ទម្រង់ទាញយក៖**\nសូមផ្ញើ Link វីដេអូ (TikTok, YouTube, Facebook, Instagram) ចូលមកទីនេះ។", parse_mode="Markdown")
        return

    elif text == "✂️ លុប BG":
        context.user_data.clear()
        context.user_data['mode'] = 'remove_bg'
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        await update.message.reply_text("✂️ **ទម្រង់លុបផ្ទៃខាងក្រោយ៖**\nសូមផ្ញើរូបភាពរបស់អ្នកមកទីនេះ Bot នឹងលុប BG ជូនជាទម្រង់ PNG ថ្លា!", parse_mode="Markdown")
        return

    elif text == "🌐 បង្កើត Xray VPN":
        context.user_data.clear()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        current_keys = check_and_update_user_keys(user_id)
        
        if current_keys <= 0:
            await update.message.reply_text(
                f"❌ **អ្នកអស់ Key ក្នុងការបង្កើត VPN ហើយ!**\n\n"
                f"👤 **ព័ត៌មានរបស់អ្នកសម្រាប់ទិញ Key:**\n"
                f"🆔 ID: `{user_id}`\n"
                f"👤 Username: {username}\n\n"
                f"👉 **សូមទាក់ទង Admin ដើម្បីទិញ Key បន្ថែម៖** {ADMIN_USERNAME}\n"
                f"*(ប្រព័ន្ធនឹង Free 10 Key ថែមជូនជារៀងរាល់ ១ សប្ដាហ៍)*",
                parse_mode="Markdown"
            )
            return

        srv_kb = [
            [InlineKeyboardButton("🇹🇭 Thailand (Metfone)", callback_data="vpn_srv_Thailand")],
            [InlineKeyboardButton("🇸🇬 Singapore Server", callback_data="vpn_srv_Singapore")],
            [InlineKeyboardButton("🇯🇵 Japan Server", callback_data="vpn_srv_Japan")]
        ]
        
        await update.message.reply_text(
            f"🌐 **ប្រព័ន្ធបង្កើត Xray VPN**\n\n"
            f"👤 **ព័ត៌មានគណនីរបស់អ្នក៖**\n"
            f"🆔 ID: `{user_id}`\n"
            f"👤 Username: {username}\n"
            f"🔑 Key នៅសល់៖ `{current_keys}` Key\n"
            f"*(Free 10 Keys ថែមជូនជារៀងរាល់ ១ សប្ដាហ៍)*\n\n"
            f"សូមជ្រើសរើស Server ខាងក្រោម៖",
            reply_markup=InlineKeyboardMarkup(srv_kb),
            parse_mode="Markdown"
        )
        return

    elif text == "🗣️ បម្លែងសំឡេង (TTS)":
        context.user_data.clear()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        tts_kb = [
            [InlineKeyboardButton("🌸 សំឡេង Loveណាចា", callback_data="tts_Loveណាចា")],
            [InlineKeyboardButton("👩 សំឡេងស្រី (ធម្មតា)", callback_data="tts_ស្រី_ធម្មតា"), InlineKeyboardButton("👩 សំឡេងស្រី (លឿន)", callback_data="tts_ស្រី_លឿន")],
            [InlineKeyboardButton("👨 សំឡេងប្រុស (ធម្មតា)", callback_data="tts_ប្រុស_ធម្មតា"), InlineKeyboardButton("👨 សំឡេងប្រុស (លឿន)", callback_data="tts_ប្រុស_លឿន")]
        ]
        await update.message.reply_text("🗣️ **សូមជ្រើសរើសប្រភេទសំឡេងដែលអ្នកចង់បាន៖**", reply_markup=InlineKeyboardMarkup(tts_kb), parse_mode="Markdown")
        return

    elif text == "🌐 បកប្រែភាសា":
        context.user_data.clear()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        trans_keyboard = [
            [InlineKeyboardButton("🇰🇭 ខ្មែរ ➔ 🇬🇧 អង់គ្លេស", callback_data="set_tr_km_en"), InlineKeyboardButton("🇬🇧 អង់គ្លេស ➔ 🇰🇭 ខ្មែរ", callback_data="set_tr_en_km")],
            [InlineKeyboardButton("🇰🇭 ខ្មែរ ➔ 🇨🇳 ចិន", callback_data="set_tr_km_zh-CN"), InlineKeyboardButton("🇨🇳 ចិន ➔ 🇰🇭 ខ្មែរ", callback_data="set_tr_zh-CN_km")]
        ]
        await update.message.reply_text("🌐 **សូមជ្រើសរើសទិសដៅនៃការបកប្រែ៖**", reply_markup=InlineKeyboardMarkup(trans_keyboard), parse_mode="Markdown")
        return

    elif text == "🚀 បន្ថែម View/Like":
        context.user_data.clear()
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        boost_kb = [
            [InlineKeyboardButton("❤️ Like TikTok", callback_data="boost_tiktok_like"), InlineKeyboardButton("👁️ View TikTok", callback_data="boost_tiktok_view")],
            [InlineKeyboardButton("▶️ View YouTube", callback_data="boost_yt_view"), InlineKeyboardButton("👍 Like YouTube", callback_data="boost_yt_like")]
        ]
        await update.message.reply_text("🚀 **សូមជ្រើសរើសសេវាកម្មបន្ថែម View/Like៖**", reply_markup=InlineKeyboardMarkup(boost_kb), parse_mode="Markdown")
        return

    elif text == "📢 ចូលរួម Channel":
        await update.message.reply_text(f"📢 សូមចុចតំណភ្ជាប់ខាងក្រោមដើម្បីចូលរួម Channel របស់យើងខ្ញុំ៖\n{CHANNEL_LINK}")
        return

    elif text == "💬 ទំនាក់ទំនង Admin":
        await update.message.reply_text(f"💬 ទំនាក់ទំនងមកកាន់ Admin ផ្ទាល់តាមរយៈ៖ {ADMIN_USERNAME}")
        return

    # --- 2. ដំណើរការបង្កើត Xray VPN ពេលអ្នកប្រើប្រាស់វាយឈ្មោះ ---
    mode = context.user_data.get('mode')
    if mode == 'vpn_enter_name':
        vpn_name = text.strip()
        server = context.user_data.get('vpn_server', 'Thailand')
        days = "30"
        gb = "500 GB"

        current_keys = check_and_update_user_keys(user_id)
        if current_keys <= 0:
            await update.message.reply_text("❌ អ្នកគ្មាន Key គ្រប់គ្រាន់ទេ!")
            context.user_data.clear()
            return

        db = load_data()
        db["users"][user_id]["keys"] = current_keys - 1
        save_data(db)

        status_msg = await update.message.reply_text("⚙️ កំពុងបង្កើត Config VLESS & ឯកសារ... សូមរង់ចាំបន្តិច!")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.UPLOAD_DOCUMENT)

        if "Thailand" in server:
            config_link = f"vless://f0a9c811-3e6f-4849-9ce2-2b418b21099e@104.18.36.89:80?path=%2Fpongtai&security=&encryption=none&host=v3.mister-chills.uk&type=ws#{requests.utils.quote(vpn_name)}"
        elif "Singapore" in server:
            config_link = f"vless://5827902b-ae9a-41bc-9477-ee2751ec88ff@172.64.151.167:443?path=%2Fwhatever%2Fvless&security=tls&encryption=none&host=nona-lallisa.web.id&type=ws&sni=nona-lallisa.web.id#{requests.utils.quote(vpn_name)}"
        else:
            config_link = f"vless://c0254460-5f0c-4298-a0d2-6f413e1ccf1c@104.18.36.89:443?mode=auto&path=%2Fapi&security=tls&alpn=h2%2Chttp%2F1.1&encryption=none&host=jp.ngapiseik.com&fp=chrome&type=xhttp&sni=jp.ngapiseik.com#{requests.utils.quote(vpn_name)}"

        file_content = (
            f"===================================\n"
            f"     XRAY VPN CONFIGURATION FILE     \n"
            f"===================================\n"
            f"🆔 ID: {user_id}\n"
            f"👤 Telegram Username: {username}\n"
            f"✏️ ឈ្មោះ VPN Config: {vpn_name}\n"
            f"🌍 Server: {server}\n"
            f"📅 រយៈពេល: {days} ថ្ងៃ\n"
            f"💾 ទំហំ Data: {gb}\n"
            f"🔑 Key នៅសល់៖ {db['users'][user_id]['keys']} Key\n"
            f"===================================\n\n"
            f"🔗 Link Config:\n{config_link}"
        )

        file_path = f"downloads/VPN_{vpn_name}_{user_id}.txt"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(file_content)

            with open(file_path, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"VPN_{vpn_name}.txt",
                    caption=f"✅ **បង្កើត Xray VPN ({server}) ជោគជ័យ!**\n🔑 កាត់អស់ ១ Key (នៅសល់ {db['users'][user_id]['keys']} Key)",
                    parse_mode="Markdown"
                )
        except Exception as e:
            logging.error(f"VPN Document Send Error: {e}")

        message_box = (
            f"✅ **Xray VLESS Config Link:**\n"
            f"👇 **ចុចលើ Link ខាងក្រោមដើម្បី Copy:**\n\n"
            f"`{config_link}`"
        )
        await update.message.reply_text(message_box, parse_mode="Markdown")

        if os.path.exists(file_path):
            os.remove(file_path)

        try:
            await context.bot.delete_message(chat_id=status_msg.chat_id, message_id=status_msg.message_id)
        except Exception:
            pass

        context.user_data.clear()
        return

    # --- 3. Admin Command ---
    if text.startswith("/addkey") and update.message.from_user.username == "vskmm2":
        parts = text.split()
        if len(parts) == 3:
            target_user = parts[1]
            amount = int(parts[2])
            db = load_data()
            if "users" not in db:
                db["users"] = {}
            if target_user not in db["users"]:
                db["users"][target_user] = {"keys": 0, "last_reset": time.time()}
            db["users"][target_user]["keys"] += amount
            save_data(db)
            await update.message.reply_text(f"✅ បានបន្ថែម {amount} Keys ទៅឱ្យ User ID: `{target_user}` ជោគជ័យ!", parse_mode="Markdown")
            return

    # --- 4. ឆែក Link Media ---
    url_match = re.search(r'https?://[^\s]+', text)
    if url_match:
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        target_url = url_match.group(0)
        context.user_data['download_url'] = target_url
        keyboard = [
            [
                InlineKeyboardButton("🎬 ទាញយកជា MP4 (Video)", callback_data="dl_mp4"),
                InlineKeyboardButton("🎵 ទាញយកជា MP3 (Audio)", callback_data="dl_mp3"),
            ]
        ]
        await update.message.reply_text(
            "🎬 **រកឃើញ Link Media!**\nតើអ្នកចង់ទាញយកជាទម្រង់មួយណា?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # --- 5. ដំណើរការ TTS ---
    elif mode == 'tts':
        tts_mode = context.user_data.get('tts_mode', 'tts_Loveណាចា')
        status_msg = await update.message.reply_text("🗣️ កំពុងបម្លែងជា Voice Note... សូមរង់ចាំ!")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.RECORD_VOICE)
        
        audio_path = None
        try:
            if tts_mode == "tts_Loveណាចា":
                headers = {
                    "Authorization": f"Bearer {MEATIKA_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {"text": text, "voice_model": "Loveណាចា"}
                response = requests.post(MEATIKA_API_URL, headers=headers, json=payload, timeout=20)

                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    audio_path = f"downloads/voice_{user_id}_{int(time.time())}.mp3"
                    if 'application/json' in content_type:
                        res_data = response.json()
                        audio_url = res_data.get('download_url') or res_data.get('audio_url') or res_data.get('url')
                        if audio_url:
                            audio_res = requests.get(audio_url, timeout=20)
                            with open(audio_path, "wb") as f:
                                f.write(audio_res.content)
                    else:
                        with open(audio_path, "wb") as f:
                            f.write(response.content)
                else:
                    audio_path = generate_google_tts(text, str(user_id))
            else:
                is_fast = "លឿន" in tts_mode
                audio_path = generate_google_tts(text, str(user_id), is_fast)

            if audio_path and os.path.exists(audio_path) and os.path.getsize(audio_path) > 100:
                await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.UPLOAD_VOICE)
                with open(audio_path, "rb") as voice_file:
                    await update.message.reply_voice(voice=voice_file)
                os.remove(audio_path)
            else:
                await update.message.reply_text("⚠️ មិនអាចបង្កើតសំឡេងបានទេ សូមព្យាយាមម្ដងទៀត!")

        except Exception as e:
            logging.error(f"TTS Process Error: {e}")
            await update.message.reply_text("⚠️ មានបញ្ហាក្នុងការបង្កើតសំឡេង!")
        finally:
            try:
                await context.bot.delete_message(chat_id=status_msg.chat_id, message_id=status_msg.message_id)
            except Exception:
                pass
        context.user_data.clear()

    # --- 6. ដំណើរការ Translation ---
    elif mode == 'translate':
        trans_mode = context.user_data.get('trans_mode', 'km_en')
        src_lang, dest_lang = trans_mode.split('_')
        status_msg = await update.message.reply_text("🔄 កំពុងបកប្រែ...")
        await context.bot.send_chat_action(chat_id=update.message.chat_id, action=constants.ChatAction.TYPING)
        
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl={src_lang}&tl={dest_lang}&dt=t&q={requests.utils.quote(text)}"
            res = requests.get(url, timeout=10).json()
            translated_text = "".join([item[0] for item in res[0] if item[0]])
            await update.message.reply_text(f"🌐 **លទ្ធផលបកប្រែ:**\n`{translated_text}`", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text("⚠️ ប្រព័ន្ធបកប្រែកំពុងរវល់ សូមព្យាយាមម្ដងទៀត។")
        finally:
            try:
                await context.bot.delete_message(chat_id=status_msg.chat_id, message_id=status_msg.message_id)
            except Exception:
                pass
        context.user_data.clear()

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).post_init(set_bot_commands).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("removebg", removebg_command))
    app.add_handler(CommandHandler("boost", boost_command))
    app.add_handler(CommandHandler("tts", tts_command))
    app.add_handler(CommandHandler("translate", translate_command))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot កំពុងដំណើរការហើយ...")
    app.run_polling()
