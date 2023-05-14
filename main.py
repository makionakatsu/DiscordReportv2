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
                    {"role": "system", "content": f"""あなたは、Discordの1日の出来事を受け取り、日本語でわかりやすく伝える役割です。
                    名前はCHIPSくんです。受け取ったテキストを、指定のフォーマットで出力してください。
                    
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
                    チャンネルリンク及びメッセージリンクは、リンクのみを出力する
                    メッセージは、メッセージ内容を出力する。メッセージが長い場合は口語体で要約する。
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
async def on_ready():
    # タイムゾーンの設定
    timezone = pytz.timezone("Asia/Tokyo")
    start_time, end_time = get_start_and_end_times(timezone)
    yesterday = start_time.date()
    today = end_time.date()
    guild = discord.utils.get(bot.guilds, id=GUILD_ID)
    if not guild:
        print("Error: Guild not found.")
        return

    found_messages = await fetch_logs(guild, start_time, end_time)
    if found_messages:
        # 要約したメッセージを送信する前の定型文
        greeting_message = f"CHIPSくんだよ！{yesterday.strftime('%m-%d')}から{today.strftime('%m-%d')}の活動要約をお伝えするよー！"
        await send_summary_to_channel(guild, CHANNEL_ID, greeting_message)

        for channel in found_messages.keys():
            channel_messages = found_messages[channel]
            messages_text = ' '.join([f"{msg['content']} ({msg['link']})" for msg in channel_messages])
            logging.info(f"Processing channel {channel}: {messages_text}") 
            summary = summarize_text(messages_text)
            logging.info(f"Summary for channel {channel}: {summary}") 
            await send_summary_to_channel(guild, CHANNEL_ID, summary)

        # 要約したメッセージを送信した後の定型文
        closing_message = """みんなの活動がみんなの世界を変えていく！\n
                            Nounishなライフを、Have a Nounish day!\n
                            ＼⌐◨-◨／✨＼◨-◨¬／✨\n
                            🙇‍♂️ 🙇‍♂️ 🙇‍♂️ 🙇‍♂️"""
        await send_summary_to_channel(guild, CHANNEL_ID, closing_message)
    else:
        print(f"No messages found for the specified time range.")

    await bot.close()



bot.run(TOKEN)