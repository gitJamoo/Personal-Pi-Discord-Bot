import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Define intents (required for modern discord.py)
intents = discord.Intents.default()
intents.message_content = True  # Allows the bot to read message content

# Initialize the bot with a command prefix
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')

@bot.command()
async def ping(ctx):
    """Responds with Pong!"""
    await ctx.send('Pong!')

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_TOKEN not found in environment. Please check your .env file.")
