# Simple osu! Discordbot

This little Project is just a small Discordbot for my own [osu! private server](https://miausu.pw) using Nextcord and our API/DB access from osu-NoLimits' bancho.py-ex installation.

## Usage:
1. Clone this repo.
2. Ensure you have Python 3.10.12 installed (it might work on higher versions, but im using 3.10.12)
3. Run `pip install -r requirements.txt && rm requirements.txt`
4. Set up your Bot and Database Credentials in the .env file.
5. Run the Bot using `python3 main.py` (This is how it starts for me, you might have to start it differently)

## Current commands:
- /eval - Only usable by you (if you own the Discord Server, or you are an Admin on it) to execute Python Code.
- /help - Shows all available commands. Also shows the Syntax to them.
- /r  - Shows the recent score.
- /top - Shows the users best score.
- /profile - Shows small infos about the User.
- /pprecord - Shows the current highest PP Score depending on the gamemode.
- /link - Supports linking a Discord User to an osu! User on your Server, which can only be changed over the Database.
- /ping - Simple ping command to check if the Bot has a good connection.
- /status - Simplest Server Status Checker that i ever created.

For any questions, DM nowoemi on Discord.
