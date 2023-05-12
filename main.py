import os
import asyncio
import aioschedule as schedule
import datetime
import nextcord as discord
from nextcord.ext import commands
import pytz
import openai


# 指定された時間帯の開始と終了の時間を取得する関数
def get_start_and_end_times(timezone):
    now = datetime.datetime.now(timezone)
    start_time = now - datetime.timedelta(days=1)
    start_time = start_time.replace(hour=20, minute=30, second=0, microsecond=0)
    end_time = now.replace(hour=20, minute=30, second=0, microsecond=0)
    return start_time, end_time


# Discordからログを取得する非同期関数
async def fetch_logs(guild, start_time, end_time):
    found_messages = {}
    for channel in guild.text_channels:
        try:
            async for msg in channel.history(limit=10000):
                if start_time <= msg.created_at <= end_time:
                    if channel.id not in found_messages:
                        found_messages[channel.id] = []
                    # メッセージの内容とリンクを辞書に格納します。
                    message_info = {
                        "content": msg.content,
                        "link": msg.jump_url
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
                    {"role": "system", "content": f"""あなたは、Discordの1日の出来事を受け取り、日本語でわかりやすく伝える役割です。
                    受け取ったテキストを、指定のフォーマットで出力してください。
                    指定フォーマット：
                    ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨ ⌐◨-◨
                    チャンネルリンク
                    チャンネル全体の話題を要約した文章
                    【話題ピックアップ】
                    ・メッセージ（メッセージリンク）
                    ・メッセージ（メッセージリンク）
                    """},
                    {"role": "user", "content": f"""
                    以下のテキストを、注意点に配慮しながら指定フォーマットに沿って出力をしてください。
                    注意点：
                    チャンネルリンクは、リンクのみを出力する
                    メッセージリンクは、リンクのみを出力する
                    【話題ピックアップ】でピックアップするメッセージは、画像やリンクを含むものを優先する。
                    ５つ程度ピックアップする。メッセージがなければピックアップしない。
                    会話のなかったチャンネルは何も出力しない。                    
                     テキスト：{chunk}
                     """}
                ]
            )
            summarized_chunks.append(response["choices"][0]["message"]["content"])
        except Exception as e:
            print(f"Error occurred during API call: {e}")
            continue

    summarized_text = "\n".join(summarized_chunks)
    return summarized_text


# 要約したメッセージをDiscordチャンネルに送信する
async def send_summary_to_channel(guild, channel_id, message):
    channel = guild.get_channel(channel_id)
    if channel is None:
        print(f"Error: Channel with ID {channel_id} not found.")
        return
    try:
        await channel.send(message)
    except discord.errors.Forbidden:
        print(f"Error: Permission denied to send message to channel {channel_id}.")


TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_CHANNEL_PAIRS = os.environ["GUILD_CHANNEL_PAIRS"].split(",")
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


found_messages = {}


async def fetch_messages():
    for pair in GUILD_CHANNEL_PAIRS:
        guild_id, channel_id = map(int, pair.split(":"))
        guild = discord.utils.get(bot.guilds, id=guild_id)
        timezone = pytz.timezone("Asia/Tokyo")
        start_time, end_time = get_start_and_end_times(timezone)

        if not guild:
            print("Error: Guild not found.")
            return

        global found_messages
        found_messages = await fetch_logs(guild, start_time, end_time)


async def send_channel_summaries():
    for pair in GUILD_CHANNEL_PAIRS:
        guild_id, channel_id = map(int, pair.split(":"))
        guild = discord.utils.get(bot.guilds, id=guild_id)
        if not guild:
            print("Error: Guild not found.")
            return

        global found_messages
        if found_messages:
            for channel in found_messages.keys():
                channel_messages = found_messages[channel]
                messages_text = ' '.join([msg["content"] for msg in channel_messages])

                summary = summarize_text(messages_text)
                await send_summary_to_channel(guild, channel_id, summary)
        else:
            print(f"No messages found for the specified time range.")


async def job():
    await fetch_messages()


async def scheduled_job():
    if datetime.datetime.now().hour == 21:
        await send_channel_summaries()


async def main():
    schedule.every(10).minutes.do(job)
    schedule.every().hour.do(scheduled_job)

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)


if __name__ == "__main__":
    bot.run(TOKEN)
    asyncio.run(main())
