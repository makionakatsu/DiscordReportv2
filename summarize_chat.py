import os
import json
import openai
from operator import itemgetter

# Get necessary environment variables
openai.api_key = os.getenv('OPENAI_API_KEY')

# Define function to summarize text using GPT
def summarize_with_gpt(text):
    # Check if the text is not empty
    if not text:
        return None

    try:
        response_summary = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-16k",
            messages=[
                {"role": "system", "content": "You are CHIPS-kun, an assistant, responsible for reviewing Discord's daily chat logs and summarizing topics comprehensively and in Japanese."},
                {"role": "user", "content": f".{text}. Please summarize the following topics of the day comprehensively in Japanese. Messages should be no longer than about 80 characters, 200 at the most."},
            ],
            max_tokens=300
        )
        summary = response_summary['choices'][0]['message']['content']
        return summary
    except Exception as e:
        print(f"Error occurred while summarizing with GPT-3.5-turbo: {e}")
        return None

# Define function to load messages from JSON file
def load_messages():
    try:
        with open('logs.json', 'r', encoding='utf-8') as f:
            messages = json.load(f)
        return messages
    except Exception as e:
        print(f"Error occurred while loading messages from JSON: {e}")
        return []

# Define function to categorize messages by channel
def categorize_messages_by_channel(messages):
    categorized_messages = {}
    for message in messages:
        channel_name = message['Channel']
        if channel_name not in categorized_messages:
            categorized_messages[channel_name] = []
        categorized_messages[channel_name].append(message)
    return categorized_messages

# Get skip channels from config file
try:
    with open('config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    skip_channels = [channel_dict['channel_id'] for channel_dict in config['skip_channels']]
except FileNotFoundError:
    print("Error: The config.json file could not be found.")
    skip_channels = []
except KeyError as e:
    print(f"Error: The key {str(e)} was not found in the config file.")
    skip_channels = []
except Exception as e:
    print(f"Error: An unexpected error occurred: {e}")
    skip_channels = []

# Define function to summarize messages
def summarize_messages(categorized_messages):
    summarized_messages = {}
    for channel, messages in categorized_messages.items():
        # Skip summary channel
        if channel in skip_channels:
            continue
        # Sort messages by reaction count
        sorted_messages = sorted(messages, key=itemgetter('ReactionCount'), reverse=True)
        # Summarize top 10 messages
        top10_messages = sorted_messages[:min(10, len(sorted_messages))]
        channel_summary = summarize_with_gpt(' '.join([message['Content'] for message in top10_messages]))
        # If the summary is None, skip this channel
        if channel_summary is None:
            continue
        # Summarize top 5 messages
        top5_messages = sorted_messages[:min(5, len(sorted_messages))]
        top5_summaries = []
        for message in top5_messages:
            summary = summarize_with_gpt(message['Content'])
            # If the summary is None, skip this message
            if summary is None:
                continue
            top5_summaries.append({
                "Summary": summary,
                "URL": message['Message URL']
            })
        # Save summary
        summarized_messages[channel] = {
            "Channel Name": channel,
            "Channel URL": messages[0]['Channel URL'],  # Get channel URL from any message
            "Channel Summary": channel_summary,
            "Top 5 Message Summaries": top5_summaries
        }
    return summarized_messages

# Define function to output summary to JSON file
def output_summary_to_json(summarized_messages):
    try:
        with open('summary.json', 'w', encoding='utf-8') as f:
            json.dump(summarized_messages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error occurred while writing to JSON: {e}")

# Define main process
def main():
    messages = load_messages()
    if messages:
        categorized_messages = categorize_messages_by_channel(messages)
        summarized_messages = summarize_messages(categorized_messages)
        output_summary_to_json(summarized_messages)

# Run main process
if __name__ == '__main__':
    main()
