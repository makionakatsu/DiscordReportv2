import os
import nextcord as discord
from nextcord.ext import commands
import datetime
import pytz
import openai


# 指定された時間帯の開始と終了の時間を取得する関数
def get_start_and_end_times(timezone):
    now = datetime.datetime.now(timezone)
    start_time = now - datetime.timedelta(days=1)
    start_time = start_time.replace(hour=20, minute=30, second=0, microsecond=0)
    end_time = now.replace(hour=20, minute=30, second=0, microsecond=0)
    return start_time, end_time

# 日本時間に変換する関数
def convert_to_jst(dt):
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    return dt.astimezone(jst)


# Discordからログを取得する非同期関数
async def fetch_logs(guild, start_time, end_time):
    found_messages = {}
    for channel in guild.text_channels:
        try:
            async for msg in channel.history(limit=10000):
                if start_time <= msg.created_at <= end_time:
                    if channel.id not in found_messages:
                        found_messages[channel.id] = []
                    # メッセージの内容とIDを辞書に格納します。
                    message_info = {
                        "content": msg.content,
                        "id": msg.id
                    }
                    found_messages[channel.id].append(message_info)
        except discord.errors.Forbidden:
            print(f"Skipping channel {channel.name} due to insufficient permissions.")
            continue
    if not found_messages:
        print(f"No messages found for the specified time range.")
    return found_messages


# メッセージの要約を生成する関数
def summarize_text(text):
    openai.api_key = OPENAI_API_KEY
    chunks = [text[i:i + 8000] for i in range(0, len(text), 8000)]
    summarized_chunks = []
    for chunk in chunks:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": """あなたは、Discordの1日の出来事を受け取り、日本語で感情を込めてわかりやすく、可愛く伝える役割です。
                     受け取ったテキストを、指定のフォーマットで出力してください。出力フォーマットは、
                    -チャンネルID
                    -チャンネルでのメッセージの要約
                    -【話題ピックアップ】として、チャンネル上のメッセージを５つ程度ピックアップする。
                    --メッセージごとにメッセージリンクをカッコで括って表示する。:メッセージ（メッセージID ）
                    --ピックアップは画像やリンクを含むものを優先する。"""},
                    {"role": "user", "content": f"""フォーマットは以下のとおりです。：
                     以下のテキストを指定フォーマットの通り出力をしてください
                     テキスト：{chunk}"""}
                ],
                timeout=60  # Increase the timeout value
            )
            summarized_chunks.append(response["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"Error occurred during API call: {e}")
            continue

    summarized_text = "\n".join(summarized_chunks)
    return summarized_text


# 要約したメッセージをDiscordチャンネルに送信する
async def send_summary_to_channel(guild, channel_id, summary):
    channel = guild.get_channel(channel_id)
    if channel is None:
        print(f"Error: Channel with ID {channel_id} not found.")
        return
    try:
        await channel.send(summary)
    except discord.errors.Forbidden:
        print(f"Error: Permission denied to send message to channel {channel_id}.")


TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
@bot.event
async def on_ready():
    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    timezone = pytz.timezone("Asia/Tokyo")
    start_time, end_time = get_start_and_end_times(timezone)

    if not guild:
        print("Error: Guild not found.")
        return

    found_messages = await fetch_logs(guild, start_time, end_time)
    
    if found_messages:
        for channel in found_messages.keys():
            channel_messages = found_messages[channel]
            messages_text = ' '.join([msg["content"] for msg in channel_messages])
            summary = summarize_text(messages_text)
            await send_summary_to_channel(guild, CHANNEL_ID, summary)
    else:
        print(f"No messages found for the specified time range.")

    # ボットのステータスを更新する
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="Discord Bot"))

    await bot.close()

bot.run(TOKEN)