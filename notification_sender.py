import argparse
import json
import os
import requests

#python notification_sender.py "Hello World" telegram

class NotificationSender:
    def __init__(self, config_path='config.json'):
        self.config = self.load_config(config_path)

    def load_config(self, config_path):
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file '{config_path}' not found. Please create it with appropriate settings.")
        with open(config_path, 'r') as file:
            return json.load(file)

    def post_to_telegram(self, message, channel_username=None):
        token = self.config.get('telegram_bot_token')
        chat_id = channel_username or self.config.get('telegram_chat_id')
        if not token or not chat_id:
            raise ValueError("Telegram bot_token and chat_id are required in config.")

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {"chat_id": chat_id, "text": message}
        response = requests.post(url, data=data)
        response.raise_for_status()
        return "Message sent successfully to Telegram."

    def post_to_slack(self, message, channel=None):
        token = self.config.get('slack_bot_token')
        channel_id = channel or self.config.get('slack_channel')
        if not token or not channel_id:
            raise ValueError("Slack bot_token and channel are required in config.")

        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        data = {"channel": channel_id, "text": message}
        response = requests.post(url, json=data)
        response.raise_for_status()
        return "Message sent successfully to Slack."

    def send_notification(self, message, platform, channel=None):
        if platform.lower() == 'telegram':
            return self.post_to_telegram(message, channel)
        elif platform.lower() == 'slack':
            return self.post_to_slack(message, channel)
        else:
            raise ValueError("Invalid platform specified. Use 'telegram' or 'slack'.")

def main():
    parser = argparse.ArgumentParser(description="Send notification to Telegram or Slack channel.")
    parser.add_argument("message", help="The message to send.")
    parser.add_argument("platform", choices=['telegram', 'slack'], help="Platform to send the notification to.")
    parser.add_argument("--channel", help="Specific channel (overrides config).")
    parser.add_argument("--config", default="config.json", help="Path to configuration file.")
    args = parser.parse_args()

    try:
        sender = NotificationSender(args.config)
        result = sender.send_notification(args.message, args.platform, args.channel)
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
