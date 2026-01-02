# Personal Pi Discord Bot

A basic Discord bot boilerplate designed to be self-hosted on a Raspberry Pi.

## Features
- Built with `discord.py`.
- Environment variable support with `python-dotenv`.
- Basic `!ping` command included.

## Prerequisites
- Python 3.8 or higher.
- A Discord Bot Token (from the [Discord Developer Portal](https://discord.com/developers/applications)).

## Setup Instructions

### 1. Clone the Repository
```bash
git clone <your-repo-url>
cd Personal-Pi-Discord-Bot
```

### 2. Configure Discord Bot
1. Create a new application in the Developer Portal.
2. Navigate to the **Bot** tab.
3. Enable **Message Content Intent** under the "Privileged Gateway Intents" section.
4. Copy your Bot Token.

### 3. Environment Setup
Create a `.env` file from the template and add your token:
```bash
cp .env.example .env
```
Edit `.env` and replace `your_token_here` with your actual token.

### 4. Installation
It is recommended to use a virtual environment:
```bash
# Create venv
python3 -m venv venv

# Activate venv
# On Linux/macOS (Raspberry Pi):
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Running the Bot
```bash
python3 bot.py
```

## Commands

### Slash Commands
- `/ping`: Responds with Pong!
- `/status_check`: Shows the current Raspberry Pi system status (CPU, RAM, Temp, etc.).

### Owner Commands
- `!sync`: Manually syncs slash commands globally. Use this if new slash commands are not appearing.

## Features
- **Status Updates**: The bot sends detailed "Online" and "Offline" status embeds to the configured `STATUS_CHANNEL_ID` channel, including host IP, OS, and uptime information.

## Hosting on Raspberry Pi (Optional)
To keep the bot running after you close the terminal, you can use `tmux`, `screen`, or set it up as a `systemd` service for automatic restarts on boot.
