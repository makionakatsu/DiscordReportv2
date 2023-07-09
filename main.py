# 必要なモジュールをインポート
import os
import nextcord as discord
from nextcord.ext import commands
import datetime
import pytz
import openai
import logging
import textwrap

# 環境変数が設定されていることを確認
if not os.getenv("DISCORD_TOKEN"):
    raise Exception("DISCORD_TOKENの環境変数が設定されていません。")
if not os.getenv("OPENAI_API_KEY"):
    raise Exception("OPENAI_API_KEYの環境変数が設定されていません。")
summary_channel_name = os.getenv("SUMMARY_CHANNEL_NAME")
if not summary_channel_name:
    raise Exception("SUMMARY_CHANNEL_NAMEの環境変数が設定されていません。")

# OpenAI APIキーをセット
openai.api_key = os.getenv("OPENAI_API_KEY")

# ログの設定
logging.basicConfig(filename=f'discord_log_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}.txt', 
                    level=getattr(logging, "ERROR".upper(), logging.ERROR), 
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# チャンネルの時間差を定義（ここでは1秒としています）
CHANNEL_TIME_DELTA = datetime.timedelta(seconds=1)

# 指定した日付と時間に対して、特定のタイムゾーンを設定する関数
def get_specific_time_on_date(date, hour, minute, second, microsecond, timezone):
    return timezone.localize(datetime.datetime(date.year, date.month, date.day, hour, minute, second, microsecond))

# 開始時間と終了時間を取得する関数
def get_start_and_end_times(timezone):
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    start_time = get_specific_time_on_date(yesterday, 20, 30, 0, 0, timezone)
    end_time = get_specific_time_on_date(today, 20, 30, 0, 0, timezone)
    return start_time, end_time

# チャンネルのログを取得し、要約する非同期関数
async def fetch_and_summarize_channel_logs(guild, start_time, end_time, summary_channel_name):
    # サマリーチャンネルを取得
    summary_channel = discord.utils.get(guild.text_channels, name=summary_channel_name)
    if summary_channel is None:
        logging.error(f"サマリーチャンネルが見つかりません。'{summary_channel_name}'が存在することを確認してください。")
        return

    # 各テキストチャンネルに対して処理を行う
    for channel in guild.text_channels:
        if channel == summary_channel:  # サマリーチャンネル自体は要約対象から除外
            continue

        try:
            end_time_channel = end_time - CHANNEL_TIME_DELTA
            # 指定した時間範囲内のメッセージを取得
            messages = await channel.history(after=start_time, before=end_time_channel, limit=None).flatten()
            if not messages:
                logging.info(f"チャンネル {channel.name}では活動がありませんでした。今日は静かでした~")
                continue

            # メッセージを要約
            contents = ' '.join([msg.content for msg in messages if not msg.author.bot])
            summarized = summarize_text(contents)
            logging.info(f"チャンネル {channel.name}の要約:\n{summarized}")
            # サマリーチャンネルに要約結果を送信
            await summary_channel.send(f"今日の{channel.name}の要約:\n{summarized}")
        except discord.errors.Forbidden:
            logging.error(f"権限が不足しているため、チャンネル {channel.name}をスキップします。")
            continue

# テキストを要約する関数
def summarize_text(text):
    chunks = textwrap.wrap(text, 2000, break_long_words=False)  # トークンの制限に合わせて調整
    summarized_chunks = []
    for chunk in chunks:
        try:
            # OpenAIのGPT-3.5-turboモデルを使ってテキストを要約
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは有益なアシスタントです。"},
                    {"role": "user", "content": f"次のテキストを要約してください: {chunk}"},
                ]
            )
            summarized_chunks.append(response['choices'][0]['message']['content'])
        except openai.api_call_error.ApiCallError as e:
            logging.error(f"OpenAI APIの呼び出しに失敗しました: {e}")
            return f"OpenAI APIの呼び出しに失敗しました: {e}"
    return ' '.join(summarized_chunks)

# インテント（Botの機能）を全て有効にしてBotを作成
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

# Botが準備できたら発火するイベント
@bot.event
async def on_ready():
    # チャンネル名が有効であることを確認する
    summary_channel = discord.utils.get(bot.guilds[0].text_channels, name=summary_channel_name)
    if not summary_channel:
        raise Exception(f"チャンネル '{summary_channel_name}' は存在しません。")
    print("{0.user}としてログインしました".format(bot))
    
    # エラーが発生した場合、エラーをログに記録し、ユーザーにメッセージを表示する
    try:
        print("リクエストを処理中...")
        jst = pytz.timezone("Asia/Tokyo")  # 日本時間を取得
        start_time, end_time = get_start_and_end_times(jst)
        # botの全てのサーバーに対して処理を行う
        for guild in bot.guilds:
            await fetch_and_summarize_channel_logs(guild, start_time, end_time, summary_channel_name)
        print("リクエストの処理が完了しました。")
    except Exception as e:
        logging.error(e)
        print(e)

# botを起動
bot.run(os.getenv("DISCORD_TOKEN"))
