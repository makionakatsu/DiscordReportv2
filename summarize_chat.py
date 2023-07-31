import os
import json
import openai
from operator import itemgetter

# 必要な環境変数を取得
openai.api_key = os.getenv('OPENAI_API_KEY')

# GPT-3.5-turboを使ってテキストを要約する関数
def summarize_with_gpt(text):
    # テキストが存在しない場合、すぐにNoneを返す
    if not text:
        return None

    try:
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "This is CHIPS-kun, an assistant who summarizes Discord chats in Japanese."},
                {"role": "user", "content": f". {text}. Could you summarize the following sentence in Japanese as short as possible without changing the meaning? If the original message is short, please summarize it even shorter."},
            ],
            max_tokens=300
        )
        summary = response_summary['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"Error occurred while summarizing with GPT-3.5-turbo: {e}")
        return None

# JSONファイルからメッセージを読み込む関数
def load_messages():
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except Exception as e:
        print(f"Error occurred while loading messages from JSON: {e}")
        return []

# メッセージをチャンネルごとに分類する関数
def categorize_messages_by_channel(messages):
    categorized_messages = {}
    for message in messages:
        channel_name = message['Channel']
        if channel_name not in categorized_messages:
            categorized_messages[channel_name] = []
        categorized_messages[channel_name].append(message)
    return categorized_messages

# スキップするチャンネルを設定ファイルから取得
try:
    with open('config.json') as f:
        config = json.load(f)
    skip_channels = [channel_dict['channel_id'] for channel_dict in config['skip_channels']]
except FileNotFoundError:
    print("Error: The config.json file could not be found.")
except KeyError as e:
    print(f"Error: The key {str(e)} was not found in the config file.")
except Exception as e:
    print(f"Error: An unexpected error occurred: {e}")

# メッセージを要約する関数
def summarize_messages(categorized_messages):
    summarized_messages = {}
    for channel, messages in categorized_messages.items():
        # スキップするチャンネルをスキップ
        if channel in skip_channels:
            continue

        # リアクション数でソート
        sorted_messages = sorted(messages, key=itemgetter('ReactionCount'), reverse=True)

        # 上位10件のメッセージを要約
        top10_messages = sorted_messages[:min(10, len(sorted_messages))]
        channel_summary = summarize_with_gpt(' '.join([message['Content'] for message in top10_messages]))

        # 上位5件のメッセージを要約
        top5_messages = sorted_messages[:min(5, len(sorted_messages))]
        top5_summaries = []
        for message in top5_messages:
            summary = summarize_with_gpt(message['Content'])
            if summary is not None:  # 要約が存在する場合のみリストに追加
                top5_summaries.append({
                    "Summary": summary,
                    "URL": message['Message URL']
                })


        # 要約を保存
        summarized_messages[channel] = {
            "Channel Name": channel,
            "Channel URL": messages[0]['Channel URL'],  # 任意のメッセージからチャンネルURLを取得
            "Channel Summary": channel_summary,
            "Top 5 Message Summaries": top5_summaries
        }
    return summarized_messages

# 要約をJSONファイルに出力する関数
def output_summary_to_json(summarized_messages):
    try:
        with open('summary.json', 'w', encoding='utf-8') as f:
            json.dump(summarized_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error occurred while writing to JSON: {e}")

# メインの処理
def main():
    messages = load_messages()
    if messages:
        categorized_messages = categorize_messages_by_channel(messages)
        summarized_messages = summarize_messages(categorized_messages)
        output_summary_to_json(summarized_messages)

if __name__ == '__main__':
    main()
