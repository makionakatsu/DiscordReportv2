import os
import nextcord as discord
from nextcord.ext import commands
import datetime
import pytz
import csv
import re

def get_start_and_end_times(timezone):
    now = datetime.datetime.now(timezone)
    start_time = now - datetime.timedelta(days=1)
    start_time = start_time.replace(hour=20, minute=30, second=0, microsecond=0)
    end_time = now.replace(hour=20, minute=30, second=0, microsecond=0)
    return start_time, end_time

def count_emojis(text):
    emoji_pattern = re.compile(
        "["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+",
        flags=re.UNICODE,
    )
    emojis = emoji_pattern.findall(text)
    return sum([len(emoji) for emoji in emojis])

def write_log_to_csv(found_messages, target_date):
    file_name = f"discord_log_{target_date}.csv"
    with open(file_name, "w", encoding="utf-8", newline="") as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow(["Timestamp", "Channel", "Author", "Content", "Message URL", "Emoji Count"])

        for msg in found_messages:
            jst_created_at = convert_to_jst(msg.created_at)
            formatted_timestamp = jst_created_at.strftime("%Y-%m-%d %H:%M:%S")
            message_url = f"https://discord.com/channels/{msg.guild.id}/{msg.channel.id}/{msg.id}"
            emoji_count = count_emojis(msg.content)
            csv_writer.writerow([formatted_timestamp, msg.channel.name, str(msg.author), msg.content, message_url, emoji_count])

    return file_name


def convert_to_jst(dt):
    utc = pytz.utc
    jst = pytz.timezone("Asia/Tokyo")
    return dt.astimezone(jst)


async def fetch_logs(guild, start_time, end_time, member=None):
    found_messages = []
    for channel in guild.text_channels:
        if not member:
            try:
                async for msg in channel.history(limit=10000):
                    if start_time <= msg.created_at <= end_time:
                        found_messages.append(msg)
            except discord.errors.Forbidden:
                print(f"Skipping channel {channel.name} due to insufficient permissions.")
                continue
        else:
            try:
                async for msg in channel.history(limit=10000, user=member):
                    if start_time <= msg.created_at <= end_time:
                        found_messages.append(msg)
            except discord.errors.Forbidden:
                print(f"Skipping channel {channel.name} due to insufficient permissions.")
                continue

    if not found_messages:
        print(f"No messages found for the specified time range.")

    return found_messages


async def send_log_to_channel(guild, log_file_name, channel_id):
    channel = guild.get_channel(channel_id)
    if channel is None:
        print(f"Error: Channel with ID {channel_id} not found.")
        return

    with open(log_file_name, "rb") as file:
        await channel.send(file=discord.File(file, filename=log_file_name))

TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])

intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}")

    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    timezone = pytz.timezone("Asia/Tokyo")
    start_time, end_time = get_start_and_end_times(timezone)

    if not guild:
        print("Error: Guild not found.")
        return

    found_messages = await fetch_logs(guild, start_time, end_time)

    if found_messages:
        target_date = start_time.strftime("%Y-%m-%d")
        log_file_name = write_log_to_csv(found_messages, target_date)
        await send_log_to_channel(guild, log_file_name, CHANNEL_ID)
    else:
        print(f"No messages found for the specified time range.")

    await bot.close()

bot.run(TOKEN)