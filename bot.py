import os
import discord
import psutil
import platform
import time
import datetime
import socket
import asyncio
import requests
import speedtest
import re
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
        self.touchpad_process = None

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

@bot.tree.command(name="public_ip", description="Get the public IP address of the bot")
async def public_ip(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    try:
        response = requests.get('https://api.ipify.org')
        ip = response.text
        await interaction.followup.send(f"🌐 Public IP: `{ip}`")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to get public IP: {e}")

@bot.tree.command(name="speedtest", description="Run an internet speed test (Takes a few seconds)")
async def run_speedtest(interaction: discord.Interaction):
    await interaction.response.defer()
    
    def test():
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Convert to Mbps
        upload = st.upload() / 1_000_000      # Convert to Mbps
        ping = st.results.ping
        return download, upload, ping

    try:
        # Run blocking speedtest in a separate thread
        loop = asyncio.get_running_loop()
        download, upload, ping = await loop.run_in_executor(None, test)
        
        embed = discord.Embed(title="🚀 Internet Speed Test", color=discord.Color.blue())
        embed.add_field(name="Download", value=f"{download:.2f} Mbps", inline=True)
        embed.add_field(name="Upload", value=f"{upload:.2f} Mbps", inline=True)
        embed.add_field(name="Ping", value=f"{ping:.2f} ms", inline=True)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Speedtest failed: {e}")

@bot.tree.command(name="remote_touchpad", description="Start remote-touchpad and get the connection link")
async def remote_touchpad(interaction: discord.Interaction):
    await interaction.response.defer()

    # Check if already running
    if bot.touchpad_process and bot.touchpad_process.returncode is None:
        # It is running, we might not have the URL handy if we didn't store it globally, 
        # but for simplicity let's just kill and restart or tell the user.
        # Better: store URL in bot instance or just restart.
        # Let's restart to ensure a fresh link/session if requested.
        try:
            bot.touchpad_process.terminate()
            await bot.touchpad_process.wait()
        except Exception:
            pass
    
    try:
        # Start the process
        # We assume 'remote-touchpad' is in the PATH
        bot.touchpad_process = await asyncio.create_subprocess_shell(
            "remote-touchpad",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        url = None
        # Read stdout to find the URL
        # We'll try to read a few lines
        max_lines = 20
        lines_read = 0
        
        while lines_read < max_lines:
            if bot.touchpad_process.stdout.at_eof():
                break
                
            line = await asyncio.wait_for(bot.touchpad_process.stdout.readline(), timeout=5.0)
            if not line:
                break
                
            decoded_line = line.decode('utf-8').strip()
            # Look for http://IP:PORT
            # Example output: "Open this URL in your smartphone's browser: http://192.168.1.x:8080"
            match = re.search(r'(http://[\d\.:]+)', decoded_line)
            if match:
                url = match.group(1)
                break
            
            lines_read += 1
            
        if url:
            await interaction.followup.send(f"📱 Remote Touchpad is running!\n**Link:** {url}\n\n⚠️ **Note:** You must be on the same network (Wi-Fi) to connect.")
        else:
            # If we didn't find a URL, maybe it failed or output format changed
            # Check stderr
            stderr_data = await bot.touchpad_process.stderr.read(1024)
            err_msg = stderr_data.decode('utf-8') if stderr_data else "Unknown error"
            
            # Kill it since it didn't seem to start correctly
            try:
                bot.touchpad_process.terminate()
            except:
                pass
                
            await interaction.followup.send(f"❌ Could not find connection URL. Output might be different or failed to start.\nError: {err_msg}")

    except asyncio.TimeoutError:
        await interaction.followup.send("❌ Timed out waiting for remote-touchpad output.")
        if bot.touchpad_process:
             try:
                bot.touchpad_process.terminate()
             except:
                pass
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to start remote-touchpad: {e}")

if __name__ == "__main__":
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("Error: DISCORD_TOKEN not found in environment.")