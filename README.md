# Telegram Channel Multiplexer

Telegram Channel Multiplexer is a utility bot that replicates messages from one or more source channels into multiple destination channels. It is designed for teams that manage many broadcast channels and want to keep their content synchronized.

## Features

- Forward messages and media from any channel where the bot is an administrator.
- Maintain the list of destination channels in a simple YAML configuration file.
- Let trusted admins enroll new channels dynamically using the `/activate` command.
- Respect a configurable delay between forwards to avoid Telegram rate limits.
- Ready for containerized deployments with the provided Dockerfile.

## Requirements

- Python 3.10+
- A Telegram bot token (obtain via [@BotFather](https://t.me/BotFather)).
- Channels where the bot is an administrator in order to read and forward messages.

## Installation

Clone the repository and install dependencies. The project uses a standard Python package layout. Creating a virtual environment keeps dependencies isolated:

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows use `.venv\\Scripts\\activate`
```

With the environment activated, install the package in editable mode:

```bash
pip install -e .
# Or install development dependencies for testing
pip install -e .[dev]
```

If you prefer requirements files:

```bash
pip install -r requirements.txt
```

## Configuration

Copy `config.example.yml` to `config.yml` and adjust the values. The bot reads its settings from `config.yml` in the project root by default, but you can override the location with the `TCM_CONFIG` environment variable.

```yaml
# config.yml
bot_token: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
source_chats:
  - -1001234567890
  - -1002222333344
target_chats:
  - chat_id: -1005555666677
  - chat_id: -1008888999900
    thread_id: 123
admin_usernames:
  - primaryadmin
  - backupadmin
delay_seconds: 1.5
```

- `bot_token`: Telegram bot token obtained from [@BotFather](https://t.me/BotFather) (can also be supplied via the `TELEGRAM_BOT_TOKEN` environment variable).
- `source_chats`: Telegram chat IDs that the bot should monitor for new messages. Only messages originating from these chats are forwarded.
- `target_chats`: Destination chats. Each entry accepts a `chat_id` and an optional `thread_id` for directing content into forum topics.
- `admin_usernames`: Telegram usernames (without `@`) allowed to administer the bot.
- `delay_seconds`: Number of seconds to wait between forwarding messages to each target. Adjust this based on the number of channels you manage (the default of 1 second works well for ~50 channels).

When an authorized admin sends `/activate` in a channel or group, the chat ID (and thread if applicable) is appended to `target_chats`. The bot immediately persists the updated configuration.

## Running the Bot

Set the bot token either in the configuration file or via the `TELEGRAM_BOT_TOKEN` environment variable, then start the process:

```bash
python -m telegram_channel_multiplexer
```

The bot uses long polling via `aiogram`. Ensure that outbound connections to Telegram are permitted from your network.

## Docker Usage

A Dockerfile is provided for reproducible deployments.

```bash
docker build -t telegram-channel-multiplexer .
docker run \
  -v $(pwd)/config.yml:/app/config.yml \
  telegram-channel-multiplexer
```

You can mount a different configuration file by supplying `-e TCM_CONFIG=/app/custom-config.yml` and binding that path into the container.

## Testing

Run the automated test suite with pytest:

```bash
pip install -e .[dev]
pytest
```

The tests cover configuration persistence, duplicate channel handling, and forwarding behaviour (including delay and error conditions) using aiogram stubs.

## Operational Considerations

- Forwarding a large number of channels may hit Telegram rate limits. The bot automatically sleeps between sends and retries gracefully when the API returns `RetryAfter` errors.
- Monitor the logs for warnings about revoked permissions. If the bot loses access to a channel, remove it from `config.yml`.
- Back up the configuration file regularly to preserve your channel list.

## License

Distributed under the MIT License. See `LICENSE` for details.
