import discord
import requests
import mysql.connector
import pymysql
import aiohttp
import datetime
import os

from discord.ext import commands
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

# THIS PROJECT IS STILL A WORK IN PROGRESS AND SHOULD NOT BE USED FOR A BIG DEMAND. I'M WARNING YOU WITH THIS, AS YOU COULD GET LIMITED BY THE OSU! API.
# THE IMPORTS ARE USED ALL OVER THE PYTHON CODE AND IF I GET RID OF mysql.connector OR pymysql EVERYTHING BREAKS FOR ME.

def calculate_mods(mods: list):
    """Calculates the mods integers together."""
    return sum(MOD_VALUES.get(mod, 0) for mod in mods)


def connect_to_db():
    """Connects to your Database using the Credentials you provided in the .env file."""
    try:
        connection = pymysql.connect(
            host="localhost", # This is most likely always localhost, as it's hosted on the VPS you own.
            database="banchopy", # This is the default Database Name provided from your bancho.py instance.
            user=dbuser,
            password=dbpassword,
            port=3306, # This is the default Database Port provided from your bancho.py instance, change if it's different
            cursorclass=pymysql.cursors.DictCursor # i honestly forgot what this is for, but without it the bot doesn't function anymore on my side
        )
        return connection
    except Error as e:
        print(f"Error: {e}")
        return None

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents, help_command=None) # Change the Prefix if you want to :)

forbidden_words = ["test", "test2"] # you can add your own words to this, to prevent users from saying the N-Word for example.

# These Values are for decoding the Mods, as defined below.
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
    """Decode the mods integer into a readable mod combo."""
    if mods_integer == 0:
        return "+NM"
    mods_list = []
    for mod, value in sorted(MOD_VALUES.items(), key=lambda x: -x[1]):  # Sort by value descending
        if mods_integer & value:  # Check if the mod is active
            mods_list.append(mod)
            mods_integer -= value
    return "+" + "".join(mods_list)


@bot.event
async def on_member_join(members):
    """This gives a new Member the Member role you defined in the .env file."""
    """The print statements are just for debugging."""
    role_name = member_role
    role = discord.utils.get(members.guild.roles, name=role_name)
    
    if role:
        await members.add_roles(role)
        print(f"Assigned {role_name} role to {members.name}")
    else:
        print(f"The Role {role_name} doesn't exist on the Server.")

@bot.command()
async def help(ctx):
    embed = discord.Embed(
        title="How do these work?",
        description="Glad that you asked!",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now()
    )

    embed.add_field(name="?help", value="Shows this Embed.", inline=False)
    embed.add_field(name="?r [-rx/-ap]", value="Shows your recent score.", inline=False)
    embed.add_field(name="?sim (maplink) (300s) (100s) (50s) (misses)", value="Simulates a Score based on your input.", inline=False)
    embed.add_field(name="?top [-rx/-ap]", value="Shows your top score.", inline=False)
    embed.add_field(name="?profile [-rx/-ap]", value="Shows your profile stats.", inline=False)
    embed.add_field(name="?pprecord [-rx/-ap]", value="Shows the pp record for the respective mode.", inline=False)
    embed.add_field(name="?link (username)",  value=f"Links your Discord Account to your {servername} Account.", inline=False)
    embed.add_field(name="?say (message)", value="Let the bot say stupid shit.", inline=False)
    embed.add_field(name="?unlink", valuef"Unlinks your Discord account from your {servername} Account.", inline=False)

    embed.set_footer(text="\"[]\" indicate that this is optional, \"()\" indicate that this is required.", icon_url="https://i.ibb.co/pKPKTJs/onlfull.png")

    await ctx.send(embed=embed)
    await ctx.message.delete()

@bot.command()
async def r(ctx, *args):
    """Gets the most recent Score of the User."""
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=recent"
    query = ""

    # Defaulting the mode, mode_id and username to nothing, to make -rx possible.
    mode = None
    mode_id = 0
    username = None

    if args and args[0] in ['-ap', '-rx', '-mania', '-ctb', '-taiko']:
        mode = args[0]
        args = args[1:]
    
    else: 
        mode = None

    if mode == '-ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == '-rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == '-mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == '-ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == '-taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0

    if args:
        username = args[0]
        query += f"&name={username}"

    # This just connects to your Database if the user already has their account linked.
    else:
        discord_id = ctx.author.id
        connection = connect_to_db()
        if not connection:
            await ctx.send("Could not connect to the Database. Please try again later.")
            await ctx.message.delete()
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await ctx.send("You have not linked your osu! account yet. Please link your account first.")
            await ctx.message.delete()
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
            await ctx.send(f"No recent scores found for {username} in the Mode {mode_name}")
            return

        if isinstance(data, list) and data:
            latest_play = data[0]
        elif isinstance(data, dict) and 'scores' in data:
            latest_play = data['scores'][0]
        else:
            await ctx.send("No recent scores found!")
            return

        player = data.get("player", {})
        username = player.get("name", "Unknown")

        user_id = player.get("id")
        avatar_url = f"https://a.{domain}/{user_id}"
        
        score = latest_play.get("score", {})
        scoreid = latest_play.get("id", 0)

        # You have to change the Emoji ID's (and maybe the names) to the ones on your Discord.
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
        mapper = beatmap.get("creator", "N/A")
        mapsr = beatmap.get("diff", "N/A")
        mapurl = f"https://{domain}/b/{mapid}"
      
        rawmappp = latest_play.get("pp", 0)
        mappp = round(rawmappp, 2)

        # This just grabs the Beatmap background from Bancho.
        mapbg = f"https://b.ppy.sh/thumb/{mapsetid}l.jpg"

        mods_integer = latest_play.get("mods", 0)

        # Here we fetch the maximum PP possible of the map (possibly also with your played mod combination)
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

        # grabbing the pp values from the osu.direct api
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

        # You possibly have to change the icon_url to your Server icon.
        embed = discord.Embed(
            title=f"{mapname} - {mapdiff} by {mapper}",
            url=f"https://{domain}/b/{mapid}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=f"Recent Score for {username}", url=f"https://{domain}/scores/{scoreid}", icon_url=f"https://a.{domain}/{user_id}")
        embed.set_thumbnail(url=mapbg)
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •   {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.miausu.pw/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="https://i.ibb.co/pKPKTJs/onlfull.png", text=f"Mode: {mode_name} • On {servername}")

        await ctx.send(embed=embed)
        await ctx.message.delete()
    else:
        await ctx.send(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")
        await ctx.message.delete()


@bot.command()
async def sim(ctx, map_link: str, n300: int, n100: int, n50: int, miss: int, *args):
    """This command is still very WIP and should not be used for daily usage, as it's still lacking on the right formatting and setup."""
    try:
        map_id = map_link.split("/")[-1]
    except:
        await ctx.send("Invalid map link! Please provide a valid map URL.")
        return

    mode = None

    if mode and args[0] in ['-ap', '-rx', '-mania', '-ctb', '-taiko']:
        args = args[0]
    else: 
        mode = args

    if mode == '-rx':
        mode_name = "Relax"
    elif mode == '-ap':
        mode_name = "Autopilot"
    elif mode == '-mania':
        mode_name = "Mania"
    elif mode == '-ctb':
        mode_name = "CatchTheBeat"
    elif mode == '-taiko':
        mode_name = "Taiko"
    else:
        mode_name = "Vanilla"

    async with aiohttp.ClientSession() as session:
        mirror_api_url = f"https://{apiurl}/pp/{map_id}"
        async with session.get(mirror_api_url) as mirror_api_response:
            if mirror_api_response.status == 200:
                mirror_data = await mirror_api_response.json()
                max_combo = mirror_data["map"]["maxCombo"]
            else:
                await ctx.send(f"Failed to fetch beatmap data. Error: {mirror_api_response.status}")
                return

    combo = max_combo - n100 - n50 - miss
    if combo < 0:
        await ctx.send("Invalid hit counts! The combo cannot be negative.")
        return

    total_hits = n300 + n100 + n50 + miss
    if total_hits == 0:
        await ctx.send("Invalid hit counts! Total hits cannot be zero.")
        return

    accuracy = ((n300 * 300 + n100 * 100 + n50 * 50) / (total_hits * 300)) * 100
    accuracy = round(accuracy, 2)

    async with aiohttp.ClientSession() as session:
        mirror_api_url = f"https://{apiurl}/pp/{map_id}"
        async with session.get(mirror_api_url) as mirror_api_response:
            if mirror_api_response.status == 200:
                mirror_api_data = await osu_direct_response.json()
                pp_100 = mirror_api_data["pp"]["100"]["pp"]
                pp_99 = mirror_api_data["pp"]["99"]["pp"]
                pp_98 = mirror_api_data["pp"]["98"]["pp"]
                pp_95 = mirror_api_data["pp"]["95"]["pp"]

                if accuracy == 100:
                    rawpp = pp_100
                elif accuracy >= 99:
                    rawpp = pp_99
                elif accuracy >= 98:
                    rawpp = pp_98
                else:
                    rawpp = pp_95

                rounded_pp = round(rawpp, 2)

                embed = discord.Embed(
                    title="Score Simulation",
                    description=f"Simulated score for map ID: {map_id}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Mode", value=mode_name, inline=True)
                embed.add_field(name="Combo", value=f"{combo}x", inline=True)
                embed.add_field(name="Misses", value=miss, inline=True)
                embed.add_field(name="Accuracy", value=f"{accuracy}%", inline=True)
                embed.add_field(name="PP", value=f"{rounded_pp}pp", inline=True)

                await ctx.send(embed=embed)
            else:
                await ctx.send(f"Failed to simulate score. Error: {osu_direct_response.status}")


@bot.command() 
async def top(ctx, *args):
    """Gets the Users best play."""
    base_url = f"https://api.{domain}/v1/get_player_scores?scope=best"
    query = ""

    mode = None
    mode_id = 0
    username = None

    if args and args[0] in ['-ap', '-rx', '-mania', '-ctb', '-taiko']:
        mode = args[0]
        args = args[1:]
    
    else: 
        mode = None

    if mode == '-ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == '-rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == '-mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == '-ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == '-taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0
        
    if args:
        username = args[0]
        query += f"&name={username}"
    
    else:
        discord_id = ctx.author.id
        connection = connect_to_db()
        if not connection:
            await ctx.send("Could not connect to the Database. Please try again later.")
            await ctx.message.delete()
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await ctx.send("You have not linked your osu! account yet. Please link your account first.")
            await ctx.message.delete()
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
            await ctx.send(f"No top scores found for {username} on {mode_name}")
            return

        if isinstance(data, list) and data:
            best_play = data[0]
        elif isinstance(data, dict) and 'scores' in data:
            best_play = data['scores'][0]
        else:
            await ctx.send("No best scores found!")
            return

        player = data.get("player", {})
        username = player.get("name", "Unknown")

        user_id = player.get("id")
        avatar_url = f"https://a.{domain}/{user_id}"

        score = best_play.get("score", {})
        scoreid = best_play.get("id", 0)

        # Change Emoji ID's (and names) to your Discord Servers.
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

        embed = discord.Embed(
            title=f"{mapname} - {mapdiff} by {mapper}",
            url=f"https://{domain}/b/{mapid}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        embed.set_author(name=f"Best Score for {username}", url=f"https://{domain}/scores/{scoreid}", icon_url=f"https://a.{domain}/{user_id}")
        embed.set_thumbnail(url=mapbg)
        embed.add_field(name="", value=f"{gradeemoji}  •  {mappp}/{fc_pp}pp  •  {accuracy:.2f}%  •  {modded_sr} :star:  •  {mods_display}\n{score_formatted}  •  x{combo}/{map_combo}  •  {n300}/{n100}/{n50}/{nmiss}  •  [Replay](https://api.{domain}/v1/get_replay?id={scoreid})", inline=False)
        embed.set_footer(icon_url="https://i.ibb.co/pKPKTJs/onlfull.png", text=f"Mode: {mode_name} • On {servername}")

        await ctx.send(embed=embed)
        await ctx.message.delete()
    else:
        await ctx.send(f"I'm sowwy UwU, but the Coding Kitties couldn't find the specified user :c Maybe this error code can help you nya? Error {response.status_code}")
        await ctx.message.delete()


@bot.command()
async def profile(ctx, *args):
    """Gets the Users profile and shows some small stats."""
    base_url = f"https://api.{domain}/v1/get_player_info?scope=stats"
    query = ""

    mode = None
    mode_id = 0
    username = None

    if args and args[0] in ['-ap', '-rx', '-mania', '-ctb', '-taiko']:
        mode = args[0]
        args = args[1:]
    
    else: 
        mode = None

    if mode == '-ap':
        mode_name = "AutoPilot"
        mode_id = 8
    elif mode == '-rx':
        mode_name = "Relax"
        mode_id = 4
    elif mode == '-mania':
        mode_name = "Mania"
        mode_id = 3
    elif mode == '-ctb':
        mode_name = "CatchTheBeat"
        mode_id = 2
    elif mode == '-taiko':
        mode_name = "Taiko"
        mode_id = 1
    else:
        mode_name = "Vanilla"
        mode_id = 0

    if args:
        username = args[0]
        query += f"&name={username}"
    
    else:
        discord_id = ctx.author.id
        connection = connect_to_db()
        if not connection:
            await ctx.send("Could not connect to the Database. Please try again later.")
            await ctx.message.delete()
            return

        cursor = connection.cursor()

        cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
        result = cursor.fetchone()

        if result:
            username = result['osu_username']
            query += f"&name={username}"
        else:
            await ctx.send("You have not linked your osu! account yet. Please link your account first.")
            await ctx.message.delete()
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
            await ctx.send(f"No stats available for {username} in mode {mode_name}")
            await ctx.message.delete()
            return

        stats_list = data['player']['stats']

        if str(mode_id) in stats_list:
            stats = stats_list[str(mode_id)]
        
            user_id = stats.get("id")
            avatar_url = f"https://a.{domain}/{user_id}"

            # You can change the Description to whatever you want, i don't really care
            embed = discord.Embed(
                title=f"{username}'s Stats",
                description=f"should we ban {username}?",
                color=discord.Color.green()
            )

            embed.set_thumbnail(url=avatar_url)
            embed.add_field(name="pp", value=stats.get("pp", "N/A"), inline=True)
            embed.add_field(name="playcount", value=stats.get("plays", "N/A"), inline=True)
            embed.add_field(name="accuracy", value=f"{stats.get('acc', 0):.2f}%", inline=True)
            embed.set_footer(text=f"mode: {mode_name}")

            await ctx.send(embed=embed)
            await ctx.message.delete()

        else:
            await ctx.send("No stats found for this mode!")
            await ctx.message.delete()
    
    else:
        await ctx.send(f"I'm sorry, but the Coding Kitties couldn't find the specified user. Error: {response.status_code}")
        await ctx.message.delete()


@bot.command()
async def pprecord(ctx, mode: str = None):
    """This gets the highest PP score for the three most played modes on osu! private servers."""
    connection = connect_to_db()
    if connection:
        cursor = connection.cursor()

        if mode == '-rx':
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' and status = '2' and mode = '4';"
            mode = "Relax"
        elif mode == '-ap':
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' AND status = '2' AND mode = '8';"
            mode = "AutoPilot"
        else:
            query = "SELECT MAX(pp) AS pprecord FROM scores WHERE grade != 'F' and status = '2' and mode = '0';"
            mode = "Vanilla"

        cursor.execute(query)

        result = cursor.fetchone()

        if result and result['pprecord'] is not None:
            pprecord = round(result['pprecord'], 2)
            await ctx.send(f"## The current PP Record for {mode} is {pprecord}pp!")
        else:
            await ctx.send("No PP Record found. :c")
        
        cursor.close()
        connection.close()
    else:
        await ctx.send("Could not connect to the database!")

# Linking Command, lets a User link their Discord account to their Profile.
@bot.command()
async def link(ctx, name: str):
    discord_id = ctx.author.id
    osu_username = name

    connection = connect_to_db()
    if not connection:
        await ctx.send("Could not connect to the Database. Please try again later.")
        await ctx.message.delete()
        return

    cursor = connection.cursor()

    cursor.execute("SELECT discord_id FROM linked_accounts WHERE osu_username = %s", (osu_username,))
    result = cursor.fetchone()

    if result:
        await ctx.send(f"The osu! account {osu_username} is already linked to another person.")
        await ctx.message.delete()
        cursor.close()
        connection.close()
        return

    cursor.execute("SELECT osu_username FROM linked_accounts WHERE discord_id = %s", (discord_id,))
    result = cursor.fetchone()

    if result:
        server_username = result['osu_username']
        await ctx.send(f"Your Discord account is already linked to your osu! account {server_username}.")
        await ctx.message.delete()
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

        await ctx.send(f"Your Discord account has been successfully linked to {server_username}")
        await ctx.message.delete()
        return 

    cursor.close()
    connection.close()

# Unlink Command, lets a user unlink their Profile.
@bot.command()
async def unlink(ctx):
    discord_id = ctx.author.id

    connection = connect_to_db()
    if not connection:
        await ctx.send("Could not connect to the Database. Please try again later.")
        await ctx.message.delete()
        return

    cursor = connection.cursor()
    cursor.execute("DELETE FROM linked_accounts WHERE discord_id = %s", (discord_id,))
    connection.commit()
    cursor.close()
    connection.close()
    await ctx.send("Successfully unlinked your Account.")
    await ctx.message.delete()
    return

# Say Command, makes the Bot say stuff.
@bot.command()
async def say(ctx, *, arg):
    """This makes the bot basically say stuff you give it."""
    """You should probably set forbidden_words up before."""
    if arg in forbidden_words:
      # This message is probably a bit harsh, eh
        await ctx.send("Shut the fuck up")
        await ctx.message.delete()
        return
    else:
        await ctx.send(arg)
        await ctx.message.delete()
        return


@bot.command()
async def status(ctx):
    """This just makes a quick GET Request to your private servers Endpoint, which is found at c.example.com"""
    url = f"https://c.{domain}"

    response = requests.get(url)

    if response.status_code == 502:
        status = "Offline"
        embed = discord.Embed(
            title=f"{servername} Server Status",
            color=discord.Color.red()
        )

        embed.add_field(name="server status", value=status, inline=False)
        
    else:
        status = "Online"
        embed = discord.Embed(
            title=f"{servername} Server Status",
            color=discord.Color.green()
        )

        embed.add_field(name="server status", value=status, inline=False)
    
    await ctx.send(embed=embed)

bot.run(bot_token)
