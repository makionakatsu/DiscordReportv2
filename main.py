import os
import pandas as pd
import openai
import datetime
import nextcord as discord
from nextcord.ext import commands
import pytz
import csv

# GitHub Secretsから各種キーを読み込む
openai.api_key = os.getenv('OPENAI_API_KEY')
guild_id = os.getenv('GUILD_ID')
summary_channel_id = os.getenv('SUMMARY_CHANNEL_ID')
discord_token = os.getenv('DISCORD_TOKEN')

# CSVファイルに出力する項目
fieldnames = ['Timestamp', 'Channel', 'Author', 'Content', 'Message URL', 'Emoji Count']

# CSVファイルを作成する関数を定義
async def write_chat_to_csv(bot):
    # 現在の日付を取得し、それを文字列形式に変換
    current_date = datetime.datetime.now().strftime("%Y-%m-%d")

    # 現在の日付を含むCSVファイル名を設定
    csv_file = f"discord_log_{current_date}.csv"

    try:
        with open(csv_file, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            for guild in bot.guilds:
                if str(guild.id) == guild_id:
                    for channel in guild.text_channels:
                        # 前日のログを取得
                        after = datetime.datetime.now() - datetime.timedelta(days=1)
                        before = datetime.datetime.now()
                        # 各メッセージに対して処理
                        async for message in channel.history(after=after, before=before):
                            writer.writerow({
                                'Timestamp': message.created_at.astimezone(pytz.timezone('Asia/Tokyo')).strftime('%Y-%m-%d %H:%M:%S'),
                                'Channel': channel.name,
                                'Author': message.author.name,
                                'Content': message.content,
                                'Message URL': message.jump_url,
                                'Emoji Count': len(message.reactions)
                            })
    except Exception as e:
        print(f"Error writing to CSV: {e}")

    return csv_file

# GPT-3.5-turboを使ってテキストを要約する関数を定義
def summarize_with_gpt(text):
    try:
        # GPT-3.5-turboを使ってテキストを要約
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You are an assistant who summarizes discord chat in Japanese."},
                {"role": "user", "content": f"Here's a discord chat: {text}. Can you summarize it for me in japanese?"},
            ],
            max_tokens=300
        )

        # 要約結果を取得
        summary = response_summary['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        summary = ""

    return summary

# Discordチャットの要約を作成する関数を定義
def summarize_discord_chat(csv_file):
    try:
        # CSVファイルを読み込み
        df = pd.read_csv(csv_file)

        # データをチャンネルと絵文字数でソート
        df_sorted = df.sort_values(['Channel', 'Emoji Count'], ascending=[True, False])

        # コメントなきもの（画像やリンクのみ）は対象外とする
        df_sorted = df_sorted[df_sorted['Content'].str.strip() != ""]

        # 各チャンネルの上位5件のコメントを取得
        top_comments = df_sorted.groupby('Channel').head(5)
        top_comments = top_comments.sort_values(['Channel', 'Emoji Count'], ascending=[True, False])

        channel_summary_dict = {}
        for channel, group in top_comments.groupby('Channel'):
            # チャンネル内の上位コメントをすべて連結
            text = ' '.join(group['Content'].values)

            # GPT-3.5-turboを使ってチャットを要約
            summary = summarize_with_gpt(text)

            # 要約結果と上位コメントを保存
            channel_summary_dict[channel] = {'summary': summary, 'top_comments': group[['Content', 'Message URL']].values.tolist()}
        
        # 絵文字のつくコメントが5件に満たなかった場合に、足りない分をランダムにピックアップ
        for channel, data in channel_summary_dict.items():
            if len(data['top_comments']) < 5:
                remaining_comments = df_sorted[df_sorted['Channel'] == channel].iloc[5:]
                additional_comments = remaining_comments.sample(5 - len(data['top_comments'])).to_dict('records')
                data['top_comments'].extend(additional_comments)
    except Exception as e:
        print(f"Error summarizing chat: {e}")
        channel_summary_dict = {}

    return channel_summary_dict

# Discordチャンネルにメッセージを送信する関数を定義
async def send_message_to_discord(bot, channel_id, message):
    try:
        # チャンネルIDからチャンネルオブジェクトを取得
        target_channel = bot.get_channel(int(channel_id))

        # メッセージを送信
        await target_channel.send(message)
    except Exception as e:
        print(f"Error sending message to Discord: {e}")

# メインの処理
if __name__ == "__main__":
    # Botの準備
    bot = commands.Bot(command_prefix='!')

    @bot.event
    async def on_ready():
        print('We have logged in as {0.user}'.format(bot))

        # CSVファイルを作成
        csv_file = await write_chat_to_csv(bot)

        # CSVファイルを読み込んでDiscordチャットを要約
        summaries = summarize_discord_chat(csv_file)

        # 各チャンネルの要約結果をDiscordチャンネルに送信
        for channel, data in summaries.items():
            message = f"======================\n"
            message += f"Channel: {channel}\n"
            message += data['summary'] + "\n"
            message += "【話題ピックアップ】\n"
            for comment, url in data['top_comments']:
                message += f"・{comment} ({url})\n"
            message += f"======================\n"

            await send_message_to_discord(bot, summary_channel_id, message)

        # 最後に作成したCSVを添付
        await bot.get_channel(int(summary_channel_id)).send(file=discord.File(csv_file))

    # Botを起動
    bot.run(discord_token)
