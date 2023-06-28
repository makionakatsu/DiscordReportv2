import os
import nextcord as discord
from nextcord.ext import commands
import datetime
from datetime import date
import pytz
import openai
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# 指定された日付と時間帯の特定の時間を取得する関数
def get_specific_time_on_date(date, hour, minute, second, microsecond, timezone):
    return timezone.localize(datetime.datetime(date.year, date.month, date.day, hour, minute, second, microsecond))

# 指定された時間帯の開始と終了の時間を取得する関数
def get_start_and_end_times(timezone):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    # 開始時間を前日の20時30分に設定
    start_time = get_specific_time_on_date(yesterday, 20, 30, 0, 0, timezone)

    # 終了時間を当日の20時30分に設定
    end_time = get_specific_time_on_date(today, 20, 30, 0, 0, timezone)

    return start_time, end_time

# 日本時間に変換する関数
def convert_to_jst(dt):
    jst = pytz.timezone("Asia/Tokyo")
    return dt.astimezone(jst)

# Discordからログを取得する非同期関数
async def fetch_logs(guild, start_time, end_time):
    found_messages = {}
    for channel in guild.text_channels:
        try:
            async for msg in channel.history(limit=5000):
                if start_time <= msg.created_at <= end_time:
                    if channel.id not in found_messages:
                        found_messages[channel.id] = []
                    # メッセージの内容、作成時間、送信者、添付ファイル、リンクを辞書に格納します。
                    message_info = {
                        "content": msg.content,
                        "created_at": msg.created_at,
                        "author": str(msg.author),
                        "attachments": [attachment.url for attachment in msg.attachments],
                        "link": msg.jump_url
                    }
                    found_messages[channel.id].append(message_info)

            # ログにメッセージ情報を記録します
            logging.info(f"Fetched messages for channel {channel.name}: {found_messages[channel.id]}")

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
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": chunk},
                    {"role": "assistant", "content": "Here is the summary:"}
                ]
            )
            summarized_chunks.append(response['choices'][0]['message']['content'])
        except openai.api_call_error.ApiCallError as e:
            print(e)
    return ' '.join(summarized_chunks)

# 各チャンネルのログを取得し、要約する非同期関数
async def summarize_channel_logs(guild, start_time, end_time):
    found_messages = await fetch_logs(guild, start_time, end_time)
    for channel in guild.text_channels:
        messages = found_messages.get(channel.id, [])
        if not messages:
            print(f"No activity in channel {channel.name}. It was quiet today~")
            continue
        contents = [message['content'] for message in messages]
        summarized = summarize_text(contents)
        print(f"Summary for channel {channel.name}:\n{summarized}")
    return

# botの設定
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

@bot.command()
async def summarize(ctx):
    print(f"Processing request from {ctx.guild.name} ...")
    jst = pytz.timezone("Asia/Tokyo")
    start_time, end_time = get_start_and_end_times(jst)
    await summarize_channel_logs(ctx.guild, start_time, end_time)
    print("Done processing request.")

# botの起動
bot.run(DISCORD_BOT_TOKEN)
