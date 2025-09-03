# Notification Sender

A Python program to send messages to private Telegram channels or Slack channels.

## Features

- Send messages to Telegram or Slack
- Configurable via JSON file
- Command-line interface for message input
- Support for overriding channel via CLI arguments

## Prerequisites

- Python 3.6+
- `requests` library (install via `pip install requests`)

## Configuration

Create a `config.json` file in the same directory as the script with the following structure:

```json
{
  "telegram": {
    "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
    "chat_id": "-YOUR_CHANNEL_ID"
  },
  "slack": {
    "bot_token": "YOUR_SLACK_BOT_TOKEN",
    "channel": "C1234567890"
  }
}
```

### Telegram Setup

1. Create a bot via [@BotFather](https://t.me/botfather) on Telegram
2. Get your BOT_TOKEN from @BotFather
3. Find your channel's chat ID:
   - Add the bot as admin to your channel
   - Send a message to the channel
   - Visit `https://api.telegram.org/bot{BOT_TOKEN}/getUpdates` to find the chat_id

### Slack Setup

1. Create a Slack app at [api.slack.com](https://api.slack.com)
2. Add `chat:write` permission to your app
3. Install the app to your workspace and get the BOT_TOKEN
4. Find your channel ID via the Slack API or channel details

## Usage

Run the script with:

```bash
python notification_sender.py "Your message here" <platform> [--channel <specific_channel>] [--config <path_to_config>]
```

### Examples

```bash
# Send to default Telegram channel
python notification_sender.py "Hello Telegram!" telegram

# Send to specific Slack channel
python notification_sender.py "Hello Slack!" slack --channel C1234567890

# Use custom config file
python notification_sender.py "Custom config message" telegram --config my_config.json
```

## Error Handling

- Validates configuration file existence and required fields
- Handles network requests and API errors gracefully
- Provides clear error messages for missing or invalid parameters

## Notes

- For private channels, ensure the bot is added as an administrator
- Test with sample configurations before using in production
