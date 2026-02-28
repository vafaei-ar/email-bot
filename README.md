# Email-to-Telegram Code Bot

A Python bot that watches your Yahoo or Gmail inbox for emails matching a subject and sender, extracts a code with a regex, sends it to a Telegram group, and auto-deletes the message after a set delay.

## Installation

### Option A: Conda (recommended)

Create and activate a conda environment, then install the Python dependencies:

```bash
conda create -n ebot python=3.11 -y
conda activate ebot
pip install -r requirements.txt
```

From the project root, run the bot with:

```bash
conda activate ebot
python run.py
```

### Option B: pip only

From the project root:

```bash
pip install -r requirements.txt
```

Then run with `python run.py` or `python -m src.main`.

## Setup

### 1. Config

Copy the example config and credentials (do not commit real credentials):

```bash
cp config.example.yaml config.yaml
cp credentials.example.yaml credentials.yaml
```

Edit `config.yaml`:

- **email.provider**: `yahoo` or `gmail`
- **email.subject_filter**: substring to match in the subject (e.g. `"Time Sensitive: Your One-Time HBO Max Code"`)
- **email.sender_filter**: substring to match in the sender address (e.g. `"hbomax@mail.hbomax.com"`)
- **email.code_pattern**: regex to extract the code (e.g. `\b\d{2}\b` for a 2-digit code). First capture group or full match is used.
- **email.poll_interval_seconds**: how often to check mail (e.g. `60`)
- **telegram.chat_id**: numeric group chat ID (see below)
- **telegram.message_delete_after_seconds**: e.g. `3600` (1 hour)
- **telegram.message_template**: optional; use `{code}` in the message (e.g. `"Code: {code}"`)

Edit `credentials.yaml` (this file is gitignored):

- **email_user**: your full email (e.g. `you@gmail.com`, `you@yahoo.com`)
- **email_password**: app password (see below)
- **telegram_bot_token**: from [@BotFather](https://t.me/BotFather)

### 2. Getting a Telegram bot token

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot`, follow the prompts, and copy the token BotFather gives you.
3. Put it in `credentials.yaml` as `telegram_bot_token`.

### 3. Getting the group chat ID

1. Add your bot to the Telegram group (as a member).
2. Send any message in the group (e.g. `hello`).
3. Open in browser: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
4. In the JSON, find `"chat":{"id": -1001234567890}`. That number is your `chat_id` (often negative for groups).
5. Put it in `config.yaml` as `telegram.chat_id`.

Alternatively, add **@userinfobot** to the group; it will reply with the group’s chat ID.

### 4. Gmail / Yahoo app password

- **Gmail**: Enable 2FA, then create an [App Password](https://myaccount.google.com/apppasswords). Use that as `email_password` (no spaces).
- **Yahoo**: Enable 2FA, then create an [app password](https://login.yahoo.com/account/security). Use that as `email_password`.

Use your normal email as `email_user` and the app password as `email_password` in `credentials.yaml`.

**Yahoo:** In [Yahoo Mail settings](https://login.yahoo.com/account/security), ensure IMAP access is enabled and use an app password (not your main password). If you see "socket error: EOF", the bot will retry automatically; also check firewall/VPN and try again later.

## Run

From the project root (so `config.yaml` and `credentials.yaml` are found):

```bash
python -m src.main
```

Or:

```bash
python run.py
```

Optional environment variables:

- **CONFIG_PATH**: path to config file (default: `config.yaml`)
- **CREDENTIALS_PATH**: path to credentials file (default: from config or `credentials.yaml` next to config)

## Behaviour

- Polls the inbox every `poll_interval_seconds`.
- Only considers emails whose subject contains `subject_filter` and whose sender contains `sender_filter`.
- Extracts the first match of `code_pattern` from the email body (plain text or HTML stripped).
- For each new matching email (by UID), sends the code to the configured Telegram group and records the UID so it is not sent again.
- Schedules deletion of that Telegram message after `message_delete_after_seconds` (best-effort; if the process restarts, some messages may not be deleted).

## License

MIT
