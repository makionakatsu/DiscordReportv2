import os
import json
import nextcord
from nextcord.ext import commands

intents = nextcord.Intents.default()
intents.message_content = True

# GitHub SecretsからAPIキーとDiscord関連の情報を読み込む
summary_channel_id = int(os.getenv('SUMMARY_CHANNEL_NAME')) 
discord_token = os.getenv('DISCORD_TOKEN')
guild_id = os.getenv('GUILD_ID')

# Discordにログインする関数
def login_discord():
    bot = commands.Bot(command_prefix='!', intents=intents)
    return bot

# summaries.jsonから要約を読み込む関数
def load_summaries():
    try:
        with open('summaries.json', 'r') as f:
            summaries = json.load(f)
        return summaries
    except Exception as e:
        print(f"Error loading summaries: {e}")
        return None

# 要約を投稿するチャンネルを見つける関数
def find_summary_channel(guild, summary_channel_id):
    try:
        return guild.get_channel(summary_channel_id)  # get_channelメソッドを使ってチャンネルを取得
    except Exception as e:
        print(f"Error finding summary channel: {e}")
        return None

# メッセージを生成する関数
def generate_messages(channel, data):
    try:
        parts = []

        # チャンネルと要約
        message = f"======================\n"
        message += f"Channel: {channel}\n"
        message += data['summary'] + "\n"
        if len(message) > 2000:
            print(f"Error: Summary for channel {channel} is too long.")
            return None
        parts.append(message)

        # トップコメント
        for comment, url in data['top_comments']:
            message = f"【話題ピックアップ】\n"
            message += f"・{comment} ({url})\n"
            message += f"======================\n"
            if len(message) > 2000:
                print(f"Error: Comment for channel {channel} is too long.")
                return None
            parts.append(message)

        return parts
    except Exception as e:
        print(f"Error generating message: {e}")
        return None

# メインの処理
if __name__ == "__main__":
    bot = login_discord()

    @bot.event
    async def on_ready():
        try:
            print(f'We have logged in as {bot.user}')

            # 指定されたギルドを取得
            guild = bot.get_guild(int(guild_id))

            # summaries.jsonから要約を読み込む
            summaries = load_summaries()
            if summaries is None:
                raise Exception("Failed to load summaries.")

            # 要約を投稿するチャンネルを探す
            summary_channel = find_summary_channel(guild, summary_channel_id)
            if summary_channel is None:
                raise Exception("Failed to find summary channel.")

            # 各チャンネルの要約と上位コメントをフォーマットに従ってメッセージに変換し、要約チャンネルに投稿
            for channel, data in summaries.items():
                messages = generate_messages(channel, data)
                if messages is not None:
                    for message in messages:
                        await summary_channel.send(message)
        except Exception as e:
            print(f"Error in on_ready: {e}")
            await bot.close()

    # Botを起動
    bot.run(discord_token)
