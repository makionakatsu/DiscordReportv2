import os
import nextcord as discord
from nextcord.ext import commands
import datetime
import pytz
import openai
import logging
import textwrap

# 環境変数が設定されていることを確認する
if not os.getenv("DISCORD_TOKEN"):
    raise Exception("The DISCORD_TOKEN environment variable is not set.")
if not os.getenv("OPENAI_API_KEY"):
    raise Exception("The OPENAI_API_KEY environment variable is not set.")
summary_channel_name = os.getenv("SUMMARY_CHANNEL_NAME")
if not summary_channel_name:
    raise Exception("The SUMMARY_CHANNEL_NAME environment variable is not set.")

# ログ設定
logging.basicConfig(filename=f'discord_log_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.txt', 
                    level=getattr(logging, "ERROR".upper(), logging.ERROR), 
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

async def fetch_and_summarize_channel_logs(guild, start_time, end_time):
    summary_channel = discord.utils.get(guild.text_channels, name=summary_channel_name)  # specify your summary channel name here
    if summary_channel is None:
        logging.error(f"Summary channel not found. Make sure '{summary_channel_name}' exists.")
        return

    for channel in guild.text_channels:
        if channel == summary_channel:  # Skip summarizing the summary channel
            continue

        try:
            end_time_channel = end_time - CHANNEL_TIME_DELTA
            messages = await channel.history(after=start_time, before=end_time_channel, limit=None).flatten()
            if not messages:
                logging.info(f"No activity in channel {channel.name}. It was quiet today~")
                continue

            contents = ' '.join([msg.content for msg in messages if not msg.author.bot])
            summarized = summarize_text(contents)
            logging.info(f"Summary for channel {channel.name}:\n{summarized}")
            # Send the summary result to the summary channel
            await summary_channel.send(f"Summary for today in {channel.name}:\n{summarized}")
        except discord.errors.Forbidden:
            logging.error(f"Skipping channel {channel.name} due to insufficient permissions.")
            continue

def summarize_text(text):
    openai.api_key = os.getenv("OPENAI_API_KEY")
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

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    # チャンネル名が有効であることを確認する
    summary_channel = discord.utils.get(bot.guilds[0].text_channels, name=summary_channel_name)
    if not summary_channel:
        raise Exception(f"The channel '{summary_channel_name}' does not exist.")
    print("We have logged in as {0.user}".format(bot))
    
    # エラーが発生した場合、エラーをログに記録し、ユーザーにメッセージを表示する
    try:
        print("Processing request...")
        jst = pytz.timezone("Asia/Tokyo")
        start_time, end_time = get_start_and_end_times(jst)
        for guild in bot.guilds:
            await fetch_and_summarize_channel_logs(guild, start_time, end_time)
        print("Done processing request.")
    except Exception as e:
        logging.error(e)
        print(e)

# botの起動
bot.run(os.getenv("DISCORD_TOKEN"))
