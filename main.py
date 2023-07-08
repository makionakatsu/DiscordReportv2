import os
import nextcord as discord
from nextcord.ext import commands
import datetime
import pytz
import openai
import logging
import textwrap

# 環境変数から情報を取得
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")  # Discordのトークン
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # OpenAIのAPIキー
LOG_LEVEL = os.getenv("LOG_LEVEL", "ERROR")  # ログのレベル
SUMMARY_CHANNEL_NAME = os.getenv("SUMMARY_CHANNEL_NAME", "summary-channel")  # サマリーチャンネル名

# ログ設定
logging.basicConfig(filename=f'discord_log_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.txt', 
                    level=getattr(logging, LOG_LEVEL.upper(), logging.ERROR), 
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

CHANNEL_TIME_DELTA = datetime.timedelta(seconds=1)

def get_specific_time_on_date(date, hour, minute, second, microsecond, timezone):
    return timezone.localize(datetime.datetime(date.year, date.month, date.day, hour, minute, second, microsecond))

def get_start_and_end_times(timezone):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    start_time = get_specific_time_on_date(yesterday, 20, 30, 0, 0, timezone)
    end_time = get_specific_time_on_date(today, 20, 30, 0, 0, timezone)
    return start_time, end_time

async def fetch_logs(guild, start_time, end_time):
    found_messages = {}
    for channel in guild.text_channels:
        try:
            end_time_channel = end_time - CHANNEL_TIME_DELTA
            messages = await channel.history(after=start_time, before=end_time_channel, limit=None).flatten()
            if messages:
                found_messages[channel.id] = [{
                    "content": msg.content,
                    "created_at": msg.created_at,
                    "author": str(msg.author),
                    "attachments": [attachment.url for attachment in msg.attachments],
                    "link": msg.jump_url
                } for msg in messages if not msg.author.bot]
        except discord.errors.Forbidden:
            logging.error(f"Skipping channel {channel.name} due to insufficient permissions.")
            continue
    if not found_messages:
        logging.info(f"No messages found for the specified time range.")
    return found_messages

def summarize_text(text):
    openai.api_key = OPENAI_API_KEY
    chunks = textwrap.wrap(text, 2000, break_long_words=False)  # adjust according to the token limit
    summarized_chunks = []
    for chunk in chunks:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": f"Please summarize the following text: {chunk}"},
                ]
            )
            summarized_chunks.append(response['choices'][0]['message']['content'])
        except openai.api_call_error.ApiCallError as e:
            logging.error(f"OpenAI API call failed: {e}")
            return f"OpenAI API call failed: {e}"
    return ' '.join(summarized_chunks)

async def summarize_channel_logs(guild, start_time, end_time):
    found_messages = await fetch_logs(guild, start_time, end_time)
    summary_channel = discord.utils.get(guild.text_channels, name=SUMMARY_CHANNEL_NAME)  # specify your summary channel name here
    if summary_channel is None:
        logging.error(f"Summary channel not found. Make sure '{SUMMARY_CHANNEL_NAME}' exists.")
        return
    for channel in guild.text_channels:
        messages = found_messages.get(channel.id, [])
        if not messages:
            logging.info(f"No activity in channel {channel.name}. It was quiet today~")
            continue
        contents = ' '.join([message['content'] for message in messages])
        summarized = summarize_text(contents)
        logging.info(f"Summary for channel {channel.name}:\n{summarized}")
        # Send the summary result to the summary channel
        await summary_channel.send(f"Summary for today in {channel.name}:\n{summarized}")
    return

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    logging.info(f"We have logged in as {bot.user}")

@bot.command()
async def summarize(ctx):
    logging.info(f"Processing request from {ctx.guild.name} ...")
    jst = pytz.timezone("Asia/Tokyo")
    start_time, end_time = get_start_and_end_times(jst)
    await summarize_channel_logs(ctx.guild, start_time, end_time)
    logging.info("Done processing request.")

# botの起動
bot.run(DISCORD_TOKEN)
