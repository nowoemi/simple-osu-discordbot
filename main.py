# this code is made by noemi (nowoemi on discord)
# if you encounter any problems, feel free to dm me on discord

import nextcord
import requests
import mysql.connector
import pymysql
import aiohttp
import datetime
import os
import random
import sys
import textwrap
import traceback
import io
import resource
import psutil
import logging
import asyncio

from nextcord.ext import commands, tasks
from nextcord import Embed
from mysql.connector import Error
from pymysql import cursors
from dotenv import load_dotenv
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

load_dotenv()

domain = os.environ["SERVERDOMAIN"]
servername = os.environ["SERVERNAME"]
bot_token = os.environ["BOT_TOKEN"]
member_role = os.environ["MEMBER_ROLE"]
member_role_id = os.environ["MEMBER_ROLE_ID"]
dbuser = os.environ["DBUSERNAME"]
dbpassword = os.environ["DBPASSWORD"]
apiurl = os.environ["MIRRORAPIURL"]
guildid = os.environ["GUILD_ID"]
playerlist = os.environ["BACKEND_USERS"]
logo = "/home/nyoemi/Shiina-Web/static/img/onlfull.png" # your logo path (internally) goes here
last_msg_id = None # keep this one None

intents = nextcord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(intents=intents)

# automatically add the member role to new members
@bot.event
async def on_member_join(member: nextcord.Member):
    role = member.guild.get_role(member_role_id)

    if role is None:
        print(f"Error: Role with ID {member_role_id} not found.")
        return

    await member.add_roles(role)
    print("Added Member Role to User")

# calculate the mod values together
def calculate_mods(mods: list):
    return sum(MOD_VALUES.get(mod, 0) for mod in mods)

# db connection
def connect_to_db():
    try:
        connection = pymysql.connect(
            host="localhost",
            database="banchopy",
            user=dbuser,
            password=dbpassword,
            port=3306,
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

# mod values taken from the osu-lazer source code available on github
MOD_VALUES = {
    "NF": 1,
    "EZ": 2,
    "HD": 8,
    "HR": 16,
    "SD": 32,
    "DT": 64,
    "RX": 128,
    "HT": 256,
    "NC": 576,
    "FL": 1024,
    "SO": 4096,
    "PF": 16416
}

def decode_mods(mods_integer):
    """Decode the mods integer into a readable mod string."""
    if mods_integer == 0:
        return "+NM"
    mods_list = []
    for mod, value in sorted(MOD_VALUES.items(), key=lambda x: -x[1]):  # Sorts by value descending
        if mods_integer & value:  # Checks if the mod is active
            mods_list.append(mod)
            mods_integer -= value
    return "+" + "".join(mods_list)

# memory limit which should be defined if you mention memory_limit() anywhere
def memory_limit(limit_in_mb: int):
    soft, hard = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (limit_in_mb * 1024 *1024, hard))

# memory usage calculation in MB
def memory_usage():
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

# Filter out the "Cleaning up" messages from the logger
class EvalFilter(logging.Filter):
    def filter(self, record):
        return "Cleaning up" not in record.getMessage()

nextcord_logger = logging.getLogger("nextcord")
nextcord_logger.addFilter(EvalFilter())

# Just gets the Playerlist from the link you defined in the .env
async def fetch_player_list():
    async with aiohttp.ClientSession() as session:
        async with session.get(playerlist) as response:
            if response.status == 200:
                text = await response.text()
                users = {}
                for line in text.splitlines():
                    if line.startswith("("):
                        id_part, user = line.split(":", 1)
                        user_id = int(id_part.strip().strip("()"))
                        user = user.strip().replace("_", " ")
                        users[user_id] = user
                return users
            else:
                return None

# generate the image using ImageDraw
def generate_image(players):
    logoimg = Image.open(logo)
    logores = logoimg.resize((200, 200))

    image = Image.new("RGB", (800, 400), color=(0, 0, 0))
    draw = ImageDraw.Draw(image)

    try:
        path = 'Montserrat-VariableFont_wght.ttf'
        # put your preferred font (^) here, but change the size if you change it and it looks weird
        font = ImageFont.truetype(font=path, size=28)
    except IOError:
        print("Custom Font not found, falling back")
        font = ImageFont.load_default()

    image.paste(logores, (10, 10))

    draw.text((220, 20), "Online Players:", fill="white", font=font)

    y_offset = 60
    if players: 
        for user_id, player in players.items():
            player_txt = f"{player} (ID: {user_id})"
            draw.text((220, y_offset), player_txt, fill="white", font=font)
            y_offset += 30
    else:
        draw.text((220, y_offset), "No users online :c", fill="white", font=font)
    
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)
    return image_bytes

# this is the function for a player list, which automatically updates every 3 minutes
@tasks.loop(minutes=3)
async def update_player_list():
    global last_msg_id

    channel = bot.get_channel(1345759393555157124)
    if channel:
        if last_msg_id:
            try:
                last_msg = await channel.fetch_message(last_msg_id)
                await last_msg.delete()
            except nextcord.NotFound:
                pass
            except nextcord.Forbidden:
                print("No Perms to delete the Message")
            except nextcord.HTTPException as e:
                print(f"Failed to delete message: {e}")
        players = await fetch_player_list()
        if players is not None:
            bot_id = 1
            higher_ids = {user_id: player for user_id, player in players.items() if user_id > bot_id}

            image_bytes = generate_image(higher_ids)
            file = nextcord.File(image_bytes, filename="players.png")
            
            msg = await channel.send(file=file)
            last_msg_id = msg.id
        else:
            msg = await channel.send("Failed to fetch players.")
            last_msg_id = msg.id

@bot.slash_command(guild_ids=[guildid], description="Replies with Pong!")
async def ping(interaction: nextcord.Interaction):
    """Simple Command to get the Bot's Ping"""
    latency: float = round(bot.latency * 1000, 2)
    await interaction.response.send_message(f"Pong! {latency} ms • Memory usage: {round(memory_usage(), 2)} MB", ephemeral=False)

@bot.slash_command(guild_ids=[guildid], description="Shows you the available Commands")
async def help(interaction: nextcord.Interaction):
    """Simple help command"""

    embed = nextcord.Embed(
        title="How do these work?",
        description="Glad that you asked!",
        color=nextcord.Color.blue(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name="/help", value="Shows this Embed.", inline=False)
    embed.add_field(name="/r [rx/ap] (username)", value="Shows your recent score.", inline=False)
    embed.add_field(name="/ping", value="Tests the connection of the Bot.", inline=False)
    embed.add_field(name="/top [rx/ap] (username)", value="Shows your top score.", inline=False)
    embed.add_field(name="/profile [rx/ap] (username)", value="Shows your profile stats.", inline=False)
    embed.add_field(name="/pprecord [rx/ap]", value="Shows the pp record for the respective mode.", inline=False)
    embed.add_field(name="/link (username)",  value=f"Links your Discord Account to your {servername} Account.", inline=False)
    embed.add_field(name="/unlink", value=f"Unlinks your Discord account from your {servername} Account.", inline=False)

    embed.set_footer(text="\"[]\" indicate that this is optional, \"()\" indicate that this is required.", icon_url="your icon url")

    await interaction.send(embed=embed)

@bot.slash_command(guild_ids=[guildid], description="Shows your most recent score.")
async def r(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    """Fetches the users most recent score."""
    await interaction.response.defer()
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=recent"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == 'taikorx':
        mode_name = "Taiko RX"
        mode_id = 5
    elif mode == 'rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == 'mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == 'ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == 'taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0

    if username:
        name = username
        print(f"{name}")
        query += f"&name={name}"
    
    else:
        discord_id = interaction.user.id
        connection = connect_to_db()
        if not connection:
            await interaction.response.send_message("Could not connect to the Database. Please try again later.")
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await interaction.response.send_message("You have not linked your osu! account yet. Please link your account first.")
            cursor.close()
            connection.close()
            return

        cursor.close()
        connection.close()

    query += f"&mode={mode_id}"

    print(f"{base_url}{query}")

    response = requests.get(base_url + query)

    if response.status_code == 200:
        data = response.json()

        if not data['scores']:
            await interaction.response.send_message(f"No recent scores found for {username} in the Mode {mode_name}")
            return

        if isinstance(data, list) and data:
            latest_play = data[0]
        elif isinstance(data, dict) and 'scores' in data:
            latest_play = data['scores'][0]
        else:
            await interaction.response.send_message("No recent scores found!")
            return

        player = data.get("player", {})
        username = player.get("name", "Unknown")

        user_id = player.get("id")
        avatar_url = f"https://a.{domain}/{user_id}"
        
        score = latest_play.get("score", {})
        scoreid = latest_play.get("id", 0)
        
        rawgrade = latest_play.get("grade", {})
        if rawgrade == "D":
            gradeemoji = "<:Drank:1321578154376298630>"
        elif rawgrade == "C":
            gradeemoji = "<:Crank:1321578122101002293>"
        elif rawgrade == "B":
            gradeemoji = "<:Brank:1321578084272701470>"
        elif rawgrade == "A":
            gradeemoji = "<:Arank:1321578040244834408>"
        elif rawgrade == "S":
            gradeemoji = "<:Srank:1321578201696309248>"
        elif rawgrade == "X":
            gradeemoji = "<:Xrank:1321578246520967208>"
        elif rawgrade == "SH":
            gradeemoji = "<:SHrank:1321578281887334471>"
        elif rawgrade == "XH":
            gradeemoji = "<:XHrank:1321578322353983529>"
        elif rawgrade == "F":
            gradeemoji = "<:Frank:1321583742099394580>"

        beatmap = latest_play.get("beatmap", {})

        score_formatted = f"{score:,}".replace(",", ".")

        combo = latest_play.get("max_combo", {})
        map_combo = beatmap.get("max_combo", {})

        mapname = beatmap.get("title", "N/A")
        mapdiff = beatmap.get("version", "N/A")
        mapsetid = beatmap.get("set_id", "N/A")
        mapid = beatmap.get("id", "N/A")
        rawmappp = latest_play.get("pp", 0)
        mappp = round(rawmappp, 2)
        mapper = beatmap.get("creator", "N/A")

        mapsr = beatmap.get("diff", "N/A")
        
        mapurl = f"https://{domain}/b/{mapid}"

        mapbg = f"https://b.ppy.sh/thumb/{mapsetid}l.jpg"

        mods_integer = latest_play.get("mods", 0)

        if mods_integer == 0:
            mirror_api_url = f"https://{apiurl}/pp/{mapid}"
        else:
            mirror_api_url = f"https://{apiurl}/pp/{mapid}?mods={mods_integer}"

        mods_display = decode_mods(mods_integer)

        n300 = latest_play.get("n300", 0)
        n100 = latest_play.get("n100", 0)
        n50 = latest_play.get("n50", 0)
        nmiss = latest_play.get("nmiss", 0)
        accuracy = latest_play.get("acc", 0)

        async with aiohttp.ClientSession() as session:
            async with session.get(mirror_api_url) as mirror_api_response:
                if mirror_api_response.status == 200:
                    mirror_data = await mirror_api_response.json()
                    fc_rawpp = mirror_data["pp"]["100"]["pp"]
                    modded_rawsr = mirror_data["difficulty"]["stars"]
                else:
                    fc_rawpp = "N/A"

        fc_pp = round(fc_rawpp, 2)
        modded_sr = round(modded_rawsr, 2)

        embed = nextcord.Embed(
            title=f"{mapname} - {mapdiff} by {mapper}",
            url=f"https://{domain}/b/{mapid}",
            color=nextcord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=f"Recent Score for {username}", url=f"https://{domain}/scores/{scoreid}", icon_url=f"https://a.{domain}/{user_id}")
        embed.set_thumbnail(url=mapbg)
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •   {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.{servername}.pw/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="https://i.ibb.co/pKPKTJs/onlfull.png", text=f"Mode: {mode_name} • On {servername}")

        await interaction.send(embed=embed)
    else:
        await interaction.response.send_message(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")

@bot.slash_command(guild_ids=[guildid], description="Shows your best play in the specified mode.")
async def top(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    """Fetches the users best play in a specified mode."""
    await interaction.response.defer()
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=best"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == 'taikorx':
        mode_name = "Taiko RX"
        mode_id = 5
    elif mode == 'rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == 'mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == 'ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == 'taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0
        
    if username:
        name = username
        query += f"&name={name}"
    
    else:
        discord_id = interaction.user.id
        connection = connect_to_db()
        if not connection:
            await interaction.send("Could not connect to the Database. Please try again later.")
            await interaction.message.delete()
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await interaction.send("You have not linked your osu! account yet. Please link your account first.")
            cursor.close()
            connection.close()
            return

        cursor.close()
        connection.close()

    query += f"&mode={mode_id}"

    response = requests.get(base_url + query)

    if response.status_code == 200:
        data = response.json()

        if not data['scores']:
            await interaction.send(f"No top scores found for {username} on {mode_name}")
            return

        if isinstance(data, list) and data:
            best_play = data[0]
        elif isinstance(data, dict) and 'scores' in data:
            best_play = data['scores'][0]
        else:
            await interaction.send("No best scores found!")
            return

        player = data.get("player", {})
        username = player.get("name", "Unknown")

        user_id = player.get("id")
        avatar_url = f"https://a.{domain}/{user_id}"

        score = best_play.get("score", {})
        scoreid = best_play.get("id", 0)

        rawgrade = best_play.get("grade", {})
        if rawgrade == "D":
            gradeemoji = "<:Drank:1321578154376298630>"
        elif rawgrade == "C":
            gradeemoji = "<:Crank:1321578122101002293>"
        elif rawgrade == "B":
            gradeemoji = "<:Brank:1321578084272701470>"
        elif rawgrade == "A":
            gradeemoji = "<:Arank:1321578040244834408>"
        elif rawgrade == "S":
            gradeemoji = "<:Srank:1321578201696309248>"
        elif rawgrade == "X":
            gradeemoji = "<:Xrank:1321578246520967208>"
        elif rawgrade == "SH":
            gradeemoji = "<:SHrank:1321578281887334471>"
        elif rawgrade == "XH":
            gradeemoji = "<:XHrank:1321578322353983529>"

        beatmap = best_play.get("beatmap", {})
        mapper = beatmap.get("creator", "N/A")

        score_formatted = f"{score:,}".replace(",", ".")

        combo = best_play.get("max_combo", {})

        map_combo = beatmap.get("max_combo", {})

        mapname = beatmap.get("title", "N/A")
        mapdiff = beatmap.get("version", "N/A")
        mapsetid = beatmap.get("set_id", "N/A")
        mapid = beatmap.get("id", "N/A")
        rawmappp = best_play.get("pp", 0)
        mappp = round(rawmappp, 2)

        mapsr = beatmap.get("diff", "N/A")
        
        mapurl = f"https://{domain}/b/{mapid}"

        mapbg = f"https://b.ppy.sh/thumb/{mapsetid}l.jpg"

        mods_integer = best_play.get("mods", 0)

        if mods_integer == 0:
            mirror_api_url = f"https://{apiurl}/pp/{mapid}"
        else:
            mirror_api_url = f"https://{apiurl}/pp/{mapid}?mods={mods_integer}"

        mods_display = decode_mods(mods_integer)

        n300 = best_play.get("n300", 0)
        n100 = best_play.get("n100", 0)
        n50 = best_play.get("n50", 0)
        nmiss = best_play.get("nmiss", 0)
        accuracy = best_play.get("acc", 0)

        async with aiohttp.ClientSession() as session:
            async with session.get(mirror_api_url) as mirror_api_response:
                if mirror_api_response.status == 200:
                    mirror_api_data = await mirror_api_response.json()
                    fc_rawpp = mirror_api_data["pp"]["100"]["pp"]
                    modded_rawsr = mirror_api_data["difficulty"]["stars"]
                else:
                    fc_rawpp = "N/A"

        fc_pp = round(fc_rawpp, 2)
        modded_sr = round(modded_rawsr, 2)

        embed = nextcord.Embed(
            title=f"{mapname} - {mapdiff} by {mapper}",
            url=f"https://{domain}/b/{mapid}",
            color=nextcord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=f"Best Score for {username}", url=f"https://{domain}/scores/{scoreid}", icon_url=f"https://a.{servername}.pw/{user_id}")
        embed.set_thumbnail(url=mapbg) 
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •   {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.{servername}.pw/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="your preferred icon url", text=f"Mode: {mode_name} • On {servername}")

        await interaction.send(embed=embed)
    else:
        await interaction.send(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")

@bot.slash_command(guild_ids=[guildid], description="Shows your profile for the specified mode.")
async def profile(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    """Fetches the users profile from the subdomain below and displays it in an embed."""
    base_url = f"https://api.{domain}/v1/get_player_info?scope=stats"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == 'taikorx':
        mode_name = "Taiko RX"
        mode_id = 5
    elif mode == 'rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == 'mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == 'ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == 'taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0

    if username:
        name = username
        query += f"&name={name}"
    
    else:
        discord_id = interaction.user.id
        connection = connect_to_db()
        if not connection:
            await interaction.send("Could not connect to the Database. Please try again later.")
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await interaction.send("You have not linked your osu! account yet. Please link your account first.")
            cursor.close()
            connection.close()
            return

        cursor.close()
        connection.close()

    query += f"&mode={mode_id}"

    response = requests.get(base_url + query)

    if response.status_code == 200:
        data = response.json()

        if not data['player']:
            await interaction.send(f"No stats available for {username} in mode {mode_name}")
            return

        stats_list = data['player']['stats']

        if str(mode_id) in stats_list:
            stats = stats_list[str(mode_id)]
        
            user_id = stats.get("id")
            avatar_url = f"https://a.{domain}/{user_id}"

            descriptions = [
                f"{username} is tapping their way into our hearts! 💕",
                f"UwU~ {username} is too powerful! pp overload detected! ✨",
                f"{username} is officially the #1 cuddle-ranked player in {servername}! 🐾",
                f"Is {username} playing osu! or just vibing with catgirls? 🐱💖",
                f"{servername}’s rhythm star {username} is shining bright today! ✨",
                f"Some say {username} can full-combo a map with just cuteness alone! 🐾",
                f"Local rhythm gamer {username} has been spotted farming... but only for pats! 🥺",
                f"Breaking news! {username} is officially too adorable to lose! 😳💞",
                f"{username} is so cracked at osu! they must be playing with cat paws! 🐾",
                f"Warning: {username} is spinning so fast they might turn into a real-life beyblade! 🔄",
                f"Rumor has it that {username} plays better when being headpatted! 🥰",
                f"{servername}’s rhythm master {username} has once again defied human limits! 🚀",
                f"PP is temporary, but {username}'s cuteness is forever! 💖",
                f"Did {username} just SS a map, or did they just charm their way to victory? 🐱✨",
                f"Cats may have nine lives, but {username} has infinite retries! 🐾",
                f"Is {username} playing osu! or just practicing their paw dexterity? 🐱",
                f"{servername}’s osu! pro {username} is back at it again with the insane scores! 🔥",
                f"Can {username} even read AR11, or are they just vibing? 🎶",
                f"If osu! had a ‘most adorable player’ rank, {username} would be #1! 💕",
                f"The {servername} council has declared {username} as the official rhythm kitten! 🐾",
                f"When {username} plays, even the {servername} kitties start cheering! 🎀🐱",
                f"Hold on—{username} is hitting 300s like they’re collecting headpats! 🎶🥺",
                f"Cuteness overload! {username} just hit a new personal best while looking adorable! 💖",
                f"{servername}’s very own osu! idol {username} is making waves again! 🌊✨",
                f"{username} might not have 100,000pp yet, but they have 100,000 cuddles waiting for them! 🥰",
                f"Will {username} ever take a break from osu!, or are they secretly a rhythm cat? 🐱🎶",
                f"Legends say {username} can hear the beat even in their dreams! 💭🎵",
                f"Welcome to {servername}, where {username} is officially the rhythm game royalty! 👑🐾"
            ]


            embed = nextcord.Embed(
                title=f"{username}'s Stats",
                description=random.choice(descriptions),
                color=nextcord.Color.green()
            )

            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="pp", value=stats.get("pp", "N/A"), inline=True)
            embed.add_field(name="playcount", value=stats.get("plays", "N/A"), inline=True)
            embed.add_field(name="accuracy", value=f"{stats.get('acc', 0):.2f}%", inline=True)
            embed.set_footer(text=f"mode: {mode_name}")

            await interaction.send(embed=embed)
        else:
            await interaction.send("No stats found for this mode!")
    
    else:
        await interaction.send(f"I'm sorry, but the Coding Kitties couldn't find the specified user. Error: {response.status_code}")

@bot.slash_command(guild_ids=[guildid], description=f"Links your Discord account to your {servername} Account.")
async def link(interaction: nextcord.Interaction, name: str):
    """Links the users Discord account to their osu! account"""
    discord_id = interaction.user.id
    osu_username = name.replace(" ", "_")

    connection = connect_to_db()
    if not connection:
        await interaction.send("Could not connect to the Database. Please try again later.")
        return

    cursor = connection.cursor()

    cursor.execute("SELECT discord_id FROM linked_accounts WHERE osu_username = %s", (osu_username,))
    result = cursor.fetchone()

    if result:
        await interaction.send(f"The osu! account {osu_username} is already linked to another person.")
        cursor.close()
        connection.close()
        return

    cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        server_username = result['osu_username']
        await interaction.send(f"Your Discord account is already linked to your osu! account {server_username}.")
        cursor.close()
        connection.close()
        return
    
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS linked_accounts (
        discord_id BIGINT PRIMARY KEY,
        osu_username VARCHAR(100) NOT NULL
    )
    """)

    cursor.execute("INSERT INTO linked_accounts (discord_id, osu_username) VALUES (%s, %s)", (discord_id, osu_username))
    connection.commit()

    cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
    osu_username = cursor.fetchone()

    if osu_username:
        server_username = osu_username['osu_username']

        await interaction.send(f"Your Discord account has been successfully linked to {server_username}")
        return 

    cursor.close()
    connection.close()

@bot.slash_command(guild_ids=[guildid], description=f"Unlinks your Discord account from your {servername} Account.")
async def unlink(interaction: nextcord.Interaction):
    """Deletes the user's linked account from the Database"""
    discord_id = interaction.user.id

    connection = connect_to_db()
    if not connection:
        await interaction.send("Could not connect to the Database. Please try again later.")
        return

    cursor = connection.cursor()
    cursor.execute("DELETE FROM linked_accounts WHERE discord_id = %s", (discord_id,))
    connection.commit()
    cursor.close()
    connection.close()
    await interaction.send("Successfully unlinked your Account.")
    return

@bot.slash_command(guild_ids=[guildid], description="Shows the PP record for the specified mode.")
async def pprecord(interaction: nextcord.Interaction, mode: str = None):
    """Fetches the PP record from your Database"""
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()

        if mode == 'ap':
            mode_name = "AutoPilot"
            mode_id = 8
        elif mode == 'taikorx':
            mode_name = "Taiko RX"
            mode_id = 5
        elif mode == 'rx':
            mode_name = "Relax"
            mode_id = 4
        elif mode == 'mania':
            mode_name = "Mania"
            mode_id = 3
        elif mode == 'ctb':
            mode_name = "CatchTheBeat"
            mode_id = 2
        elif mode == 'taiko':
            mode_name = "Taiko"
            mode_id = 1
        else:
            mode_name = "Vanilla"
            mode_id = 0

        query = f"SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F'  AND status = '2' AND mode = '{mode_id}'"

        cursor.execute(query)

        result = cursor.fetchone()

        if result and result['pprecord'] is not None:
            pprecord = round(result['pprecord'], 2)
            await interaction.send(f"## The current PP Record for {mode_name} is {pprecord}pp!")
        else:
            await interaction.send("No PP Record found. :c")
        
        cursor.close()
        connection.close()
    else:
        await interaction.send("Could not connect to the database!")

@bot.slash_command(guild_ids=[guildid], description=f"Checks the Server Status for {servername}")
async def status(interaction: nextcord.Interaction):
    url = f"https://c.{domain}"

    response = requests.get(url)

    if response.status_code == 502:
        status = "Offline"
        embed = nextcord.Embed(
            title=f"{servername} Server Status",
            color=nextcord.Color.red()
        )

        embed.add_field(name="server status", value=status, inline=False)
        
    else:
        status = "Online"
        embed = nextcord.Embed(
            title=f"{servername} Server Status",
            color=nextcord.Color.green()
        )

        embed.add_field(name="server status", value=status, inline=False)
    
    await interaction.send(embed=embed)

@bot.slash_command(guild_ids=[guildid], description=f"meow")
async def eval(interaction: nextcord.Interaction, *, code: str) -> None:
    """A dangerous command to run Python Code and return the result"""
    logging.basicConfig(filename="eval_logs.txt", level=logging.INFO)

    if interaction.user.id != your_id: # and interaction.user.id != 1239307325798617261:
        logging.info(f" User {interaction.user.id} tried to execute {code}")
        await interaction.send("hell no")
        return

    if any(keyword in code.lower() for keyword in ["for", "os.environ", "os.system", "eval(", "exec(", "shutil"]):
        await interaction.send("nice try buddy") # this check here basically prevents any potential VPS crashes due to ram usage
        return
    
    memory_limit(150)
    
    exec_namespace = {**globals(), **locals(), **{mod.__name__: mod for mod in sys.modules.values()}}

    # Indents the code for the async function
    indented_code = textwrap.indent(textwrap.dedent(code), '    ')
    wrapped_code = f"""
async def _execute():
{indented_code}
"""

    try:
        output = io.StringIO()
        sys.stdout = output
        # Executes the wrapped code
        exec(wrapped_code, exec_namespace)
        # Awaits the result of the async function
        result = await asyncio.wait_for(exec_namespace["_execute"](), timeout=5.0)
        logging.info(f" User {interaction.user.id} executed {code}")
        # Sends the result to the channel
        sys.stdout = sys.__stdout__
        captured_output = output.getvalue()
        await interaction.response.defer()
        await interaction.send(captured_output)
    except Exception:
        # Sends the error traceback to the channel
        await interaction.response.defer()
        await interaction.send(f"Error: {traceback.format_exc()}")

@bot.event
async def on_ready():
    await bot.sync_application_commands()
    update_player_list.start()
    print("Bot started!")

bot.run(bot_token)