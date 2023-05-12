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
GUILD_ID = int(os.environ["GUILD_ID"])
CHANNEL_ID = int(os.environ["CHANNEL_ID"])
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]


intents = discord.Intents.default()
intents.messages = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ボットが準備完了した時に実行されるイベント
@bot.event
async def on_ready():
    await send_greeting()
    await send_channel_summaries()
    await send_farewell()
    # ボットを閉じる
    await bot.close()


# 昨日の日付を取得して、挨拶メッセージを送信する
async def send_greeting():
    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    if not guild:
        print("Error: Guild not found.")
        return

    # 昨日の日付を取得
    yesterday = datetime.datetime.now(pytz.timezone("Asia/Tokyo")) - datetime.timedelta(days=1)
    greeting = f"こんばんは！今日もCHIPSくんが{yesterday.month}月{yesterday.day}日のまとめをやっていくよー！"

    # 最初の挨拶を投稿
    await send_summary_to_channel(guild, CHANNEL_ID, greeting)

# チャンネルごとの要約を取得して、それぞれ送信する
async def send_channel_summaries():
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

# 最後に終わりの挨拶メッセージを送信する
async def send_farewell():
    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    if not guild:
        print("Error: Guild not found.")
        return

    farewell = "みんなの活動がみんなの世界を変えていく！Nounishなライフを、Have a Nounish day！"

    # 最後の挨拶を投稿
    await send_summary_to_channel(guild, CHANNEL_ID, farewell)


bot.run(TOKEN)
