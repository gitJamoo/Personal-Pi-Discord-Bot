import os
import discord
import psutil
import platform
import time
import datetime
import socket
from typing import Optional
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

# Try importing gpiozero for Pi specific features
try:
    from gpiozero import CPUTemperature
    is_raspberry_pi = True
except (ImportError, OSError):
    is_raspberry_pi = False

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
STATUS_CHANNEL_ID = os.getenv('STATUS_CHANNEL_ID')

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.start_time = None

    async def setup_hook(self):
        # This syncs the commands to Discord. 
        # In production, you might want to sync to specific guilds for faster updates.
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

    async def get_system_embed(self, status, color):
        hostname = socket.gethostname()
        local_ip = get_local_ip()
        
        uname = platform.uname()
        system_os = f"{uname.system} {uname.release}"
        
        # Current time
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y-%m-%d %H:%M:%S")

        embed = discord.Embed(title=f"Bot Status: {status}", color=color, timestamp=now)
        embed.add_field(name="Hostname", value=hostname, inline=True)
        embed.add_field(name="Host IP", value=local_ip, inline=True)
        embed.add_field(name="OS", value=system_os, inline=True)
        
        if status == "Online":
             embed.add_field(name="Start Time", value=timestamp_str, inline=False)
        elif status == "Offline" and self.start_time:
             uptime_duration = now - self.start_time
             embed.add_field(name="Session Duration", value=str(uptime_duration).split('.')[0], inline=False)
             embed.add_field(name="Shutdown Time", value=timestamp_str, inline=False)

        # Network Interfaces (Brief)
        net_io = psutil.net_if_addrs()
        active_interfaces = []
        for interface_name, interface_addresses in net_io.items():
            for address in interface_addresses:
                if str(address.family) == 'AddressFamily.AF_INET':
                     if address.address != '127.0.0.1':
                        active_interfaces.append(f"{interface_name}: {address.address}")
        
        if active_interfaces:
            embed.add_field(name="Network Interfaces", value="\n".join(active_interfaces[:5]), inline=False)

        return embed

    async def on_ready(self):
        self.start_time = datetime.datetime.now()
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('------')
        
        # Send Online Message
        if STATUS_CHANNEL_ID:
            try:
                channel = self.get_channel(int(STATUS_CHANNEL_ID))
                if channel:
                    embed = await self.get_system_embed("Online", discord.Color.green())
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"Failed to send online message: {e}")

    async def close(self):
        # Send Offline Message before closing connection
        if STATUS_CHANNEL_ID:
            try:
                # We need to fetch the channel again or use the cached one
                channel = self.get_channel(int(STATUS_CHANNEL_ID))
                if channel:
                    embed = await self.get_system_embed("Offline", discord.Color.red())
                    await channel.send(embed=embed)
            except Exception as e:
                print(f"Failed to send offline message: {e}")
        
        await super().close()

bot = MyBot()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("🚫 You do not have permission to use this command.")
    elif isinstance(error, commands.CommandNotFound):
        pass # Ignore unknown commands
    else:
        await ctx.send(f"⚠️ An error occurred: {error}")
        print(f"Command Error: {error}")

@bot.command()
@commands.is_owner()
async def sync(ctx, spec: Optional[str] = None):
    """
    Syncs slash commands.
    Usage:
    !sync - Global sync (can take up to an hour)
    !sync guild - Sync to current guild (instant)
    """
    try:
        if spec == "guild":
            bot.tree.copy_global_to(guild=ctx.guild)
            synced = await bot.tree.sync(guild=ctx.guild)
            await ctx.send(f"✅ Synced {len(synced)} command(s) to the current guild.")
        else:
            synced = await bot.tree.sync()
            await ctx.send(f"✅ Synced {len(synced)} command(s) globally. Note: Global updates may take up to an hour to propagate.")
    except Exception as e:
        await ctx.send(f"❌ Failed to sync commands: {e}")

@bot.tree.command(name="ping", description="Responds with Pong!")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Pong!")

@bot.tree.command(name="status_check", description="Shows the Raspberry Pi system status")
async def status_check(interaction: discord.Interaction):
    # System Info
    uname = platform.uname()
    system_os = f"{uname.system} {uname.release}"
    
    # Uptime
    boot_time = psutil.boot_time()
    current_time = time.time()
    uptime_seconds = current_time - boot_time
    uptime_string = str(datetime.timedelta(seconds=int(uptime_seconds)))

    # CPU
    cpu_usage = psutil.cpu_percent(interval=None) # interval=None is non-blocking
    
    # Temperature
    if is_raspberry_pi:
        try:
            cpu_temp = CPUTemperature().temperature
            temp_str = f"{cpu_temp:.1f}°C"
        except Exception:
            temp_str = "N/A"
    else:
        temp_str = "N/A (Not on Pi)"

    # Memory
    memory = psutil.virtual_memory()
    ram_usage = f"{memory.used / (1024**3):.2f}GB / {memory.total / (1024**3):.2f}GB ({memory.percent}%)"

    # Disk
    disk = psutil.disk_usage('/')
    disk_usage = f"{disk.used / (1024**3):.2f}GB / {disk.total / (1024**3):.2f}GB ({disk.percent}%)"

    embed = discord.Embed(title="🥧 Raspberry Pi Status", color=discord.Color.green())
    embed.add_field(name="OS", value=system_os, inline=True)
    embed.add_field(name="Uptime", value=uptime_string, inline=True)
    embed.add_field(name="CPU Usage", value=f"{cpu_usage}%", inline=True)
    embed.add_field(name="CPU Temp", value=temp_str, inline=True)
    embed.add_field(name="RAM", value=ram_usage, inline=False)
    embed.add_field(name="Disk (Root)", value=disk_usage, inline=False)
    embed.set_footer(text=f"Requested by {interaction.user.display_name}")

    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_TOKEN not found in environment.")