import nextcord
import requests
import mysql.connector
import pymysql
import aiohttp
import datetime
import os

from nextcord.ext import commands
from nextcord import Embed
from mysql.connector import Error
from pymysql import cursors
from dotenv import load_dotenv

load_dotenv()

domain = os.environ["SERVERDOMAIN"]
servername = os.environ["SERVERNAME"]
bot_token = os.environ["BOT_TOKEN"]
member_role = os.environ["MEMBER_ROLE"]
dbuser = os.environ["DBUSERNAME"]
dbpassword = os.environ["DBPASSWORD"]
apiurl = os.environ["MIRRORAPIURL"]
guildid = os.environ["GUILD_ID"]

intents = nextcord.Intents.default()
intents.message_content = True
bot = commands.Bot(intents=intents)

@bot.event
async def on_ready():
    await bot.sync_application_commands()
    print("We ball")

def calculate_mods(mods: list):
    return sum(MOD_VALUES.get(mod, 0) for mod in mods)

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
    """Decode mods integer into a readable mod string."""
    if mods_integer == 0:
        return "+NM"
    mods_list = []
    for mod, value in sorted(MOD_VALUES.items(), key=lambda x: -x[1]):  # Sort by value descending
        if mods_integer & value:  # Check if the mod is active
            mods_list.append(mod)
            mods_integer -= value
    return "+" + "".join(mods_list)

@bot.slash_command(guild_ids=[guildid], description="Replies with Pong!")
async def ping(interaction: nextcord.Interaction):
    await interaction.response.send_message("Pong!", ephemeral=False)

@bot.slash_command(guild_ids=[guildid], description="Shows you the available Commands")
async def help(interaction: nextcord.Interaction):

    embed = nextcord.Embed(
        title="How do these work?",
        description="Glad that you asked!",
        color=nextcord.Color.blue(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name="/help", value="Shows this Embed.", inline=False)
    embed.add_field(name="/r [rx/ap] (username)", value="Shows your recent score.", inline=False)
    embed.add_field(name="/top [rx/ap] (username)", value="Shows your top score.", inline=False)
    embed.add_field(name="/profile [rx/ap] (username)", value="Shows your profile stats.", inline=False)
    embed.add_field(name="/pprecord [rx/ap]", value="Shows the pp record for the respective mode.", inline=False)
    embed.add_field(name="/link (username)",  value=f"Links your Discord Account to your {servername} Account.", inline=False)
    embed.add_field(name="/unlink", value=f"Unlinks your Discord account from your {servername} Account.", inline=False)

    embed.set_footer(text="\"[]\" indicate that this is optional, \"()\" indicate that this is required.", icon_url="https://i.ibb.co/pKPKTJs/onlfull.png")

    await interaction.send(embed=embed)

@bot.slash_command(guild_ids=[guildid], description="Shows your most recent score.")
async def r(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    await interaction.response.defer()
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=recent"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
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
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •   {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.miausu.pw/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="https://i.ibb.co/pKPKTJs/onlfull.png", text=f"Mode: {mode_name} • On {servername}")

        await interaction.send(embed=embed)
    else:
        await interaction.response.send_message(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")

@bot.slash_command(guild_ids=[guildid], description="Shows your best play in the specified mode.")
async def top(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    await interaction.response.defer()
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=best"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
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

        embed.set_author(name=f"Best Score for {username}", url=f"https://{domain}/scores/{scoreid}", icon_url=f"https://a.miausu.pw/{user_id}")
        embed.set_thumbnail(url=mapbg)
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •  {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.{domain}/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="https://i.ibb.co/pKPKTJs/onlfull.png", text=f"Mode: {mode_name} • On {servername}")

        await interaction.send(embed=embed)
    else:
        await interaction.send(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")

@bot.slash_command(guild_ids=[guildid], description="Shows your profile for the specified mode.")
async def profile(interaction: nextcord.Interaction, username: str = None, mode: str = None):
    base_url = f"https://api.{domain}/v1/get_player_info?scope=stats"
    query = ""

    mode_id = 0

    if mode == 'ap':
        mode_name = "AutoPilot"
        mode_id = 8
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

            embed = nextcord.Embed(
                title=f"{username}'s Stats",
                description=f"should we ban {username}?",
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
    discord_id = interaction.user.id
    osu_username = name

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
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()

        if mode == 'rx':
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' and status = '2' and mode = '4';"
            mode = "Relax"
        elif mode == 'ap':
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' AND status = '2' AND mode = '8';"
            mode = "AutoPilot"
        else:
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' and status = '2' and mode = '0';"
            mode = "Vanilla"

        cursor.execute(query)

        result = cursor.fetchone()

        if result and result['pprecord'] is not None:
            pprecord = round(result['pprecord'], 2)
            await interaction.send(f"## The current PP Record for {mode} is {pprecord}pp!")
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

bot.run(bot_token)
