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
            summary_channel = find_summary_channel(guild, summary_channel_name)
            if summary_channel is None:
                raise Exception("Failed to find summary channel.")

            # 各チャンネルの要約と上位コメントをフォーマットに従ってメッセージに変換し、要約チャンネルに投稿
            for channel, data in summaries.items():
                message = generate_message(channel, data)
                if message is not None:
                    await summary_channel.send(message)
        except Exception as e:
            print(f"Error in on_ready: {e}")
            await bot.close()

    # Botを起動
    bot.run(discord_token)
