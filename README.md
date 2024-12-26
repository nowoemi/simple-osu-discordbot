# Simple osu! Discordbot

This little Project is just a small Discordbot for my own [osu! private server](https://miausu.pw) using discord.py and our API/DB access from osuAkatsuki's bancho.py installation.

## Usage:
1. Clone this repo.
2. Ensure you have Python 3.9 installed (it might work on higher versions, but im using 3.9)
3. Run `pip install -r requirements.txt && rm requirements.txt`
4. Set up your Bot and Database Credentials in the .env file.
5. Run the Bot using `python3.9 main.py`

## Current commands:
- ?help - Shows all available commands. Also shows the Syntax to them.
- ?r  - Shows the recent score.
- ?sim - Simulated a score from a map that the user provides. (Currently only possible with the Vanilla Ruleset)
- ?top - Shows the users best score.
- ?profile - Shows small infos about the User.
- ?pprecord - Shows the current highest PP Score depending on the gamemode.
- ?link - Supports linking a Discord User to an osu! User on your Server, which can only be changed over the Database.
- ?say - Makes the Bot say stuff, but you can also control what words are allowed, and what words are not.
- ?status - Simplest Server Status Checker that i ever created.

For any questions, DM pupgvrl on Discord.
