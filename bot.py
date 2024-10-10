import enum
import discord
from discord import app_commands
from discord import Intents, Client, Embed, ui
from discord.ext import commands, ipcx
import tempfile
import traceback
import google.generativeai as genai
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from important_stuff.interactive_jobs import accounting
import os
import ctypes
import llms
import io
import contextlib
import ctypes.util
from dotenv import load_dotenv
import uuid
import requests
import sys
import redis
from typing import Literal
import json
import logging
import subprocess
import important_stuff.modals as job_modals
import psycopg2
from psycopg2 import sql
from time import sleep
import time
import string
from important_stuff import main_guild
import asyncio
from rate_limiter import check_rate_limit
import mysql.connector
import datetime
from datetime import timedelta
from important_stuff.permission import moderator_permissions, admin_permissions
from important_stuff.weatherservice import get_forecast, get_current_forecast, get_alerts
from important_stuff.custom_checks import has_permissions
from important_stuff.checkingphotos import optimize_image

import random
import tempfile 
#from Bank.items_service import ItemsService

# handler = logging.FileHandler(filename=f"{datetime.datetime.now().strftime('%Y-%m-%d')}-bot.log", encoding="utf-8", mode="w")
# handler
load_dotenv()

DEV_MODE = None

try:
    a = ctypes.util.find_library('opus')
    print(a)
    discord.opus.load_opus(a)
    print("Loaded opus")
except Exception as e:
    print("Couldn't load opus")

get_ipv4 = subprocess.getoutput("curl -s ifconfig.me")

print("Loaded on IP: ", get_ipv4)

ip = None
token = None

if get_ipv4 == "":
    DEV_MODE = True
    print("Currently on local machine")
    ip = "127.0.0.1"
    print("Using Dev Token")
    token = os.getenv("DISCORD_BOT_DEV_TOKEN")
else:
    DEV_MODE = False
    print("On server ip")
    ip = get_ipv4
    print("Using Main Token")
    token = os.getenv("DISCORD_BOT_TOKEN")

redis_client = redis.Redis(host=os.getenv("RATELIMIT_REDIS_HOST"), port=os.getenv("RATELIMIT_REDIS_PORT"), db=0, username=os.getenv("RATELIMIT_REDIS_USERNAME"), password=os.getenv("RATELIMIT_REDIS_PASSWORD"))
redis_dm_client = redis.Redis(host=os.getenv("DM_REDIS_HOST"), port=os.getenv("DM_REDIS_PORT"), db=0, username=os.getenv("DM_REDIS_USERNAME"), password=os.getenv("DM_REDIS_PASSWORD"))
redis_timeout_client = redis.Redis(host=os.getenv("TIMEOUT_REDIS_HOST"), port=os.getenv("TIMEOUT_REDIS_PORT"), db=0, username=os.getenv("TIMEOUT_REDIS_USERNAME"), password=os.getenv("TIMEOUT_REDIS_PASSWORD"))
#client = MongoClient("")
guild_backups = MongoClient()
#redis_application_client = redis.Redis(host="", port=, db=, username="", password="")


#items_service = ItemsService() 
monitored_guild = None
channel_map = {}
maintenance_mode = False
def load_items():
    with open("Gamble/items.json") as f:
        items = json.load(f)
    return items
with open("suggestions.json", "r") as f:
    suggestions = json.load(f)

guild_db = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user=os.getenv("MYSQL_USER"),
    password=os.getenv("MYSQL_PASS"),
    database=os.getenv("MYSQL_DB"),
    port=os.getenv("MYSQL_PORT") 
)

guild_db.autocommit = True
guild_db.reconnect(attempts=3, delay=5)

connector = psycopg2.connect(
    dbname="",
    user="",
    password="",
    host="",
    port=""
)

postcurse = connector.cursor() 
postcurse.connection.autocommit = True

def keep_alive(mycursor):
    while True:
        mycursor.execute("SELECT * FROM guilds")
        print("Keeping alive")
        sleep(3600) # did it not push???


mycursor = guild_db.cursor(buffered=True)
intents = Intents.all()

class Caliente(discord.Client):
    def __init__(self, *, intents: discord.Intents, **options):
        super().__init__(intents=intents)
        self.ipc = ipcx.Server(self, secret_key="", host=ip)

    
    async def setup_hook(self):
       await self.ipc.start()
    async def on_ready(self):
        if DEV_MODE:
            await caliente.change_presence(activity=discord.Game(name="Developer Bot"))
            print("Bot is using dev token")
        else:
            watching = discord.Activity(type = discord.ActivityType.watching, name=f"{len(self.guilds)} servers")
            await self.change_presence(activity=watching)
        for guild in self.guilds:
            mycursor.execute("SELECT guild_id FROM guilds")
            db_guilds = {row[0] for row in mycursor.fetchall()}
            bot_guilds = {str(guild.id) for guild in self.guilds}
            guilds_to_remove = db_guilds - bot_guilds
            for guild_id in guilds_to_remove:
                delete_guild = "DELETE FROM guilds WHERE guild_id = %s"
                mycursor.execute(delete_guild, (guild_id,))
            guild_db.commit()
        print(f"Logged on as {self.user.name}")
        print("Syncing Commands")
        for guild in self.guilds:
            try:
                tree.copy_global_to(guild=guild)
                await tree.sync(guild=guild)
                print(f"Synced {len(tree.get_commands())} commands for {guild.name}")
                await asyncio.sleep(2)
            except discord.HTTPException:
                pass
        self.total_members = sum(guild.member_count for guild in self.guilds)
        self.total_guilds = len(self.guilds)
        guild_description = "No description!"
        channel_id = None
        suggestions_channel = None
        bot_name_in_guild = self.user.name
        mute_role = None
        bot_updates = "False"
        channel_id2 = None
        reputation_channel = None
        if not DEV_MODE:
            for guild in self.guilds:
                guild_id = str(guild.id)
                mycursor.execute("SELECT * FROM guild_profiles WHERE guild_id = %s", (guild_id,))
                result_profiles = mycursor.fetchone()
                mycursor.execute("SELECT * FROM guilds WHERE guild_id = %s", (guild_id,))
                result_guilds = mycursor.fetchone()
                mycursor.execute("SELECT * FROM guilds_with_bot_updates WHERE guild_id = %s", (guild_id,))
                result_guilds_with_bot_updates = mycursor.fetchone()
                if result_profiles is None:
                    sql2 = "INSERT INTO guild_profiles (guild_name, description, guild_id) VALUES (%s, %s, %s)"
                    val2 = (guild.name, guild_description, str(guild.id))
                    mycursor.execute(sql2, val2)
                    print(f"Inserted data for guild {guild.name} in guild_profiles")    
                if result_guilds is None:
                    sql = "INSERT INTO guilds (guild_id, guild_name, channel_id, bot_name_in_guild, mute_role, suggestions_channel, reputation_channel) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    val = (str(guild.id), guild.name, channel_id, bot_name_in_guild, mute_role, suggestions_channel, reputation_channel)
                    mycursor.execute(sql, val)
                    print(f"Inserted data for guild {guild.name} in guilds")
                if result_guilds_with_bot_updates is None:
                    sql = "INSERT INTO guilds_with_bot_updates (guild_id, bot_updates, channel_id) VALUES (%s, %s, %s)"
                    val2 = (str(guild.id), bot_updates, channel_id2)
                    mycursor.execute(sql, val2)
                    print(f"Inserted data for guild {guild.name} in guilds_with_bot_updates")
            guild_db.commit()
            print("Updated Database")
        else:
            print("Dev mode, queries were not executed")
        # online_channel = self.get_channel()
        # await online_channel.send("Bot is online")  
        
    async def on_ipc_ready(self):
       print("IPC Server is ready")

    async def on_ipc_error(self, endpoint, error):
       print(f"An error occurred on endpoint {endpoint}: {error}")

    

caliente = Caliente(intents=intents, heartbeat_timeout=120, max_ratelimit_timeout=240.0)
tree = app_commands.CommandTree(caliente)

def can_work(job_name: str):
    async def predicate(interaction: discord.Interaction):
        print(f"User ID: {interaction.user.id}")
        postcurse.execute("SELECT job FROM currency WHERE user_id = %s", (str(interaction.user.id),))
        user_job = postcurse.fetchone()
        print(f"User Job: {user_job}")
        if user_job is not None and user_job[0] == job_name:
            return True
        else:
            await interaction.response.send_message("You do not have this job", ephemeral=True)
            return False
    return app_commands.check(predicate)

header = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": "Bot " + str(caliente.http.token)
    }

# async def item_autocomplete(interaction: discord.Interaction, current: str):
#     # Filter items based on current input
#     return [discord.app_commands.Choice(name=item, value=item) for item in all_items if current.lower() in item.lower()]



caliente.total_members = 0
caliente.total_guilds = caliente.fetch_guilds()

intents.guilds = True

# testing = discord.Guild

# test2 = testing.audit_logs(limit=1, action=discord.AuditLogAction.ban).flatten()

intents.invites = True
"""Logging Events"""
@caliente.event
async def on_member_ban(guild: discord.Guild, user: discord.Member):
    logs = guild.audit_logs(limit=1, action=discord.AuditLogAction.ban)
    guild_id = guild.id
    mycursor.execute("SELECT channel_id FROM guilds WHERE guild_id = %s", (str(guild_id),))
    print(guild.id)
    ban_embed = discord.Embed(title="Bot-Bot Logs")
    channel_id = mycursor.fetchone()
    if channel_id is None:
        return
    channel_id = int(channel_id[0])
    print(f"Channel ID: {channel_id}")
    channel = caliente.get_channel(channel_id)
    print(f"Channel: \n {channel}")
    async for log in logs:
        if log.target == user:
            ban_embed.set_author(name="Ban")
            ban_embed.add_field(name="User", value=log.target, inline=True)
            ban_embed.add_field(name="Moderator", value=log.user, inline=True)
            ban_embed.add_field(name="Reason", value=log.reason, inline=False)
            ban_embed.set_footer(text=f"{datetime.datetime.now()}")
            await channel.send(embed=ban_embed)

@caliente.event
async def on_blacklist(guild_id):
    guild = caliente.get_guild(guild_id)
    owner_id = guild.owner_id
    owner = caliente.get_user(owner_id)
    mycursor.execute("SELECT guild_id FROM blacklisted WHERE guild_id = %s", (guild_id,))
    blacklisted_guild = mycursor.fetchone()
    await owner.send("Your guild has been blacklisted")
    await guild.leave()
    if blacklisted_guild is not None:
        return True
    else:
        return False

@caliente.event
async def on_interaction(interaction: discord.Interaction):
    if maintenance_mode == True:
        await interaction.response.send_message("The bot is in maintenance mode, no commands will be executed", ephemeral=False)
        interaction.command_failed = True
    try:
        print(f"{interaction.user.name} executed: {interaction.data['name']}")
    except Exception as e:
        print(f"{interaction.user.name} executed a command but an error occured. Most likely a button press but heres the error just incase: {e}")

@caliente.event
async def on_button_click(interaction: discord.Interaction):
    try:
        print(f"{interaction.user.name} clicked the button")
    except Exception as e:
        print(f"{interaction.user.name} clicked the button and an error occured: {e}")
async def testing_connection(data):
    return print("Connection is working")


@caliente.ipc.route()
async def changeloggingchannel(data):
    guild_id = data.guild_id
    channel_id = data.channel_id
    mycursor.execute("UPDATE guilds SET channel_id = %s WHERE guild_id = %s", (channel_id, guild_id))
    guild_db.commit()
    print(f"{guild_id} has been updated to {channel_id}")
    return "Updated logging channel"

@caliente.ipc.route()
async def changesuggestionchannel(data):
    guild_id = data.guild_id
    channel_id = data.channel_id
    mycursor.execute("UPDATE guilds SET suggestions_channel = %s WHERE guild_id = %s", (channel_id, guild_id))
    guild_db.commit()
    print(f"{guild_id} has been updated to {channel_id}")
    return "Updated suggestions channel"
@caliente.ipc.route()
async def changemuterole(data):
    guild_id = data.guild_id
    role_id = data.role_id
    mycursor.execute("UPDATE guilds SET mute_role = %s WHERE guild_id = %s", (role_id, guild_id))
    print(f"{guild_id} has been updated to {role_id}")
    return "Updated mute role"

@caliente.ipc.route()
async def blacklistguild(data):
    guild_id = data.guild_id
    guild = caliente.get_guild(guild_id)
    owner_id = guild.owner_id
    guild_name = guild.name
    mycursor.execute("INSERT INTO blacklisted (guild_id, owner_id, guild_name) VALUES (%s)", (guild_id,), (owner_id,), (guild_name,))
    guild_db.commit()
    print(f"Blacklisted {guild_name}")
    caliente.dispatch("blacklist", guild_id)

@caliente.ipc.route()
async def get_guilds(data):
    return len(caliente.guilds)

@caliente.ipc.route()
async def get_guild_ids(data):
    return [guild.id for guild in caliente.guilds]

@caliente.ipc.route()
async def get_all_guilds_and_other_stuff(data):
    guilds = []
    for guild in caliente.guilds:
        guilds.append({
            "name": guild.name,
            "id": guild.id,
            "channels": [{"name": channel.name, "id": channel.id} for channel in guild.channels],
            "member_count": guild.member_count,
            "icon_url": guild.icon.url if guild.icon else None
        })
    return guilds
@caliente.ipc.route()
async def user_information(data):
    user_id = data.user_id
    postcurse.execute("SELECT reputation FROM user_reputation WHERE user_id = %s", (str(user_id),))
    reputation = postcurse.fetchone()
    postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(user_id),))
    money = postcurse.fetchone()
    if money is None:
        money = "You are yet to start your economic journey"
    
    user_data = {
        "reputation": reputation,
        "balance": money
    }

    return user_data

@caliente.ipc.route()
async def get_guild(data):
    guild = caliente.get_guild(data.guild_id)
    print(f"Recieved Request for guild {guild.name}")
    #mycursor.execute("SELECT reputation FROM guild_profiles WHERE guild_id = %s", (str(guild.id),))
    #guild_reputation = mycursor.fetchone()
    
    if guild is None: 
        return None
    try:
        invites = await guild.invites()
        invite_codes = [invite.code for invite in invites]
    except discord.Forbidden:
        invite_codes = []

    guild_data = {
        "name": guild.name,
        "id": guild.id,
        "channels": [{"name": channel.name, "id": channel.id} for channel in guild.channels if channel.type != discord.ChannelType.category],
        "member_count": guild.member_count,
        "members": [{"name": member.name, "bot": member.bot} for member in guild.members],
        "icon_url": guild.icon.url if guild.icon else None,
        #"reputation": guild_reputation,
        "active_invites": invite_codes,
        "bot_permissions": guild.me.guild_permissions.value,
        "roles": [
            {
                "name": role.name,
                "id": role.id, 
                "permissions": [permissions for permissions in role.permissions if permissions is not None]
            } for role in guild.roles],
    }    
    return guild_data
@caliente.ipc.route()
async def get_role_data(data):
    guild = caliente.get_guild(data.guild_id)
    role = guild.get_role(data.role_id)
    role_data = {
        "name": role.name,
        "id": role.id,
        "permissions": [permissions for permissions in role.permissions if permissions is not None]
    }
    return role_data

@caliente.ipc.route()
async def get_members(data):
    guild = caliente.get_guild(data.guild_id)
    members = [{"name": member.name, 
                "bot": member.bot,
                "id": member.id,
                "created_at": member.created_at
                } for member in guild.members]
    return members

@caliente.ipc.route()
async def member_data(data):
    guild = caliente.get_guild(data.guild_id)
    member = guild.get_member(data.member_id)
    member = [
        {
            "name": member.name,
            "bot": member.bot,
            "id": member.id,
            "roles": [role.name for role in member.roles],
            "permissions": [permissions for permissions in member.guild_permissions if permissions is not None],
            "avatar_url": member.avatar.url if member.avatar else "No avatar",
            "status": member.status,
            "nitro": member.premium_since if member.premium_since else "Not a nitro user",
            "related_servers": [guild.name for guild in member.mutual_guilds if guild.name is not None]
        }
        
    ]
    return member


@caliente.event
async def on_guild_remove(guild: discord.Guild):
    print(f"Left guild {guild.name}")
    channel_id = main_guild.guild_channels["Guild left"]
    if not DEV_MODE:
        mycursor.execute("DELETE FROM guilds WHERE guild_id = %s", (guild.id,))
        mycursor.execute("DELETE FROM guild_profiles WHERE guild_id = %s", (guild.id,))
        mycursor.execute("DELETE FROM guilds_with_bot_updates WHERE guild_id = %s", (guild.id,))
        guild_db.commit()
        print("Updated Database")
    else:
        print("Dev mode, queries were not deleted")
    channel = caliente.get_channel(channel_id)
    if channel is not None:
        await channel.send(f"Left guild {guild.name}")
    else:
        print(f"Couldn't find channel with ID {channel_id}")
    
@caliente.event
async def on_guild_join(guild: discord.Guild):
    try:
        print(f"Syncing {len(tree.get_commands())} commands for {guild.name}")
        tree.copy_global_to(guild=guild)
        await tree.sync(guild=guild)
        print(f"Synced {len(tree.get_commands())} commands for {guild.name}")
        await asyncio.sleep(0.5)
    except discord.HTTPException:
        pass
    guild_description = "No description!"
    channel_id = None
    bot_name_in_guild = caliente.user.name
    suggestion_channel = None
    mute_role = None
    owner_id = guild.owner_id
    print(f"Joined guild {guild.name}")
    channel_id = None
    reputation_channel = None
    guild_id = str(guild.id)
    mycursor.execute("SELECT * FROM guilds WHERE guild_id = %s", (guild_id,))
    exsisting_guild = mycursor.fetchone()
    if exsisting_guild is None:
        sql = "INSERT INTO guilds (guild_id, guild_name, channel_id, bot_name_in_guild, mute_role, suggestions_channel, reputation_channel) VALUES (%s, %s, %s, %s, %s, %s, %s)"
        sql2 = "INSERT INTO guild_profiles (guild_name, description, guild_id) VALUES (%s, %s, %s)"
        val = (str(guild.id), guild.name, channel_id, bot_name_in_guild, mute_role, suggestion_channel, reputation_channel)
        val2 = (guild.name, guild_description, str(guild.id))
        mycursor.execute(sql, val)
        mycursor.execute(sql2, val2)
        await asyncio.sleep(0.5)
        guild_db.commit()
        print("Updated database")
        mycursor.execute("SELECT guild_id FROM blacklisted WHERE guild_id = %s", (guild_id,))
    blacklisted_guild = mycursor.fetchone()

    if blacklisted_guild is not None:
        # If the guild is blacklisted, send a message to the guild owner
        owner = caliente.get_user(owner_id)
        if owner is not None:
            await owner.send("Your guild is blacklisted.")
        await guild.leave()
        return  # Exit the function if the guild is blacklisted

@caliente.event

async def on_guild_update(before, after):
    if before.name != after.name:
        mycursor.execute("UPDATE guilds SET guild_name = %s WHERE guild_id = %s", (after.name, after.id))
        mycursor.execute("UPDATE guild_profiles SET guild_name = %s WHERE guild_id = %s", (after.name, after.id))
        guild_db.commit()
        print(f"Updated guild name from {before.name} to {after.name}")
@caliente.event
async def on_message(message: discord.Message):
    if isinstance(message.channel, discord.DMChannel):
        guild = caliente.get_guild(662945359244558336)  # Ensure your bot is part of this guild
        if guild:
            channel = guild.get_channel(1234722221776437248)  # The channel where the thread will be created
            if channel:
                # Check if a thread already exists for this user, otherwise create one
                thread_name = f"DM from {message.author.display_name}"
                thread = discord.utils.get(channel.threads, name=thread_name)
                if thread is None:
                    # Create a new thread if it doesn't exist
                    thread = await channel.create_thread(name=thread_name, message=None,auto_archive_duration=60)  # Time in minutes before auto-archive

                # Send the received DM content to the thread
                await thread.send(f"**{message.author.display_name}**: {message.content}")

                # Increment the Redis counter for this user
                redis_dm_client.incr(f"dm:{message.author.id}")

        else:
            print("Guild or channel not found.")
        local_vars = {
        "caliente": caliente,
        "interaction": discord.Interaction,
        "discord": discord,
        "app_commands": app_commands,
        "commands": commands,
        "bot": caliente,
        "mysql": mysql,
        "mycursor": mycursor,
        "redis_timeout_client": redis_timeout_client,
        "uuid": uuid
    }

    if message.author.id != 489061310022156302:
        return
    
    if message.content.startswith("eval"):
        code = message.content[5:-3]
        try:
            exec(code, local_vars)
        except Exception as e:
            await message.channel.send(f"```{e}```")
        else:
            await message.channel.send("```Executed```")



@tree.error

async def on_error(interaction: discord.Interaction, error: app_commands.errors):
    embed = Embed(title="An error occured", description=f"```{error}```", color=discord.Color.red())
    exc_info = sys.exc_info()
    tb = traceback.extract_tb(exc_info[2])
    filename, line, func, text = tb[-1]
    print(f"{interaction.user.name} | {interaction.user.id}: {error} | line: {line}")
    if interaction.response.type == discord.InteractionResponseType.deferred_channel_message:
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)
"""Weather commands"""

# class PageTurner(discord.ui.View):
#     def __init__(self, embeds, start_page=0):
#         super().__init__()
#         self.embeds = embeds
#         self.current_page = start_page
#         if len(self.embeds) == 1:
#             self.current_page = 0

#     @discord.ui.button(label='Previous', style=discord.ButtonStyle.grey, disabled=True)
#     async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
#         if self.current_page > 0:
#             self.current_page -= 1
#             await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

#         # Disable the "Previous" button if we're on the first page
#         if self.current_page == 0:
#             button.disabled = True
#         else:
#             button.disabled = False

#         await interaction.message.edit(view=self)

#     @discord.ui.button(label='Next', style=discord.ButtonStyle.grey, disabled=False)
#     async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
#         if self.current_page < len(self.embeds) - 1:
#             self.current_page += 1
#             await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

#         # Enable the "Previous" button if we're not on the first page
#         if self.current_page != 0:
#             self.previous.disabled = False

#         # Disable the "Next" button if we're on the last page
#         if self.current_page == len(self.embeds) - 1:
#             button.disabled = True
#         else:
#             button.disabled = False

#         await interaction.message.edit(view=self)
    
# @tree.command(
#     name="alerts",
#     description="Returns the current weather alerts for the given location"
# )
# @caliente.event

# async def alerts(interaction: discord.Interaction, location: str):
#     try:
#         user_id = interaction.user.id
#         if not check_rate_limit(user_id, "alerts", 10, 180):
#             await interaction.response.send_message("You are using this command too much.", ephemeral=True)
#             return
#         if location.isdigit():
#             embeds = get_alerts(location)
#         elif ", " in location:
#             city, state = location.split(", ")
#             embeds = get_alerts(city, state)
#         else:
#             city = location
#             embeds = get_alerts(city)

#         view=PageTurner(embeds)
#         await interaction.response.send_message(embed=embeds[0], view=view)
#     except KeyError: 
#         await interaction.response.send_message("This is an invalid location, try again")

#     # Send the initial message with the first page of alerts and the PageTurner view
@tree.command(
    name="weather",
    description="Returns the current weather for the given location"
)

@caliente.event
async def weather(interaction: discord.Interaction, location: str):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "weather", 5, 1800):
        await interaction.response.send_message("You have reached your limit, wait 30 minutes again", ephemeral=True)
        return
    if location.isdigit():
        embed_var = get_current_forecast(zipcode=location)
    elif ", " in location:
        city, state = location.split(", ")
        embed_var = get_current_forecast(city, state)
    else:
        city = location
        embed_var = get_current_forecast(city)
    await interaction.response.send_message(embed=embed_var)
@weather.error

async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.app_commands.errors.CommandInvokeError):
        await interaction.response.send_message("This is an invalid location, try again")
# @tree.command(
#     name="forecast",
#     description="Returns the weather forecast for the given location"
# )

# @caliente.event

# async def forecast(interaction: discord.Interaction, location: str):
#     state = None  # Define state here so it always exists
#     if location.isdigit():
#         embed_var = get_forecast(zipcode=location)
#     elif ", " in location:
#         city, state = location.split(", ")
#         embed_var = get_forecast(city, state)
#     else:
#         city = location
#         embed_var = get_forecast(city, state)
#     await interaction.response.send_message(embed=embed_var)
"""Guild Profile commands"""
@tree.command(
    name="setguilddescription",
    description="Sets the description for the guild"
)

@app_commands.checks.has_permissions(administrator=True)
@caliente.event

async def setguilddescription(interaction: discord.Interaction, description: str):
    guild_id = str(interaction.guild.id)
    sql = "UPDATE guild_profiles SET description = %s WHERE guild_id = %s"
    val = (description, guild_id)
    mycursor.execute(sql, val)
    guild_db.commit()
    await interaction.response.defer(thinking=True, ephemeral=False)
    await interaction.followup.send(f"Guild description set to {description}")

@setguilddescription.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")

"""Work commands"""
# work_commands = app_commands.Group(name="work", description="A bunch of work commands")

# @work_commands.command(
#     name="dronepilot",
#     description="Time to fly some drones"
# )

# @can_work('droneoperator')

# @caliente.event
# async def dronepilot(interaction: discord.Interaction):
#     operatingdrone = ["DV-Predator M7", "MK V Reaper", "DS5-Aurora", "GQS-Flamer", "JX-9 ThunderBolt", "MoLoToV-Irchai", "Phantom-Wing", "A4-Sunfyre"]
#     await interaction.response.send_message("You will be operating the...")
#     await asyncio.sleep(5)
#     drone = random.choice(operatingdrone)
#     await interaction.edit_original_response(content=f"You will be operating the {drone} drone.")
#     await asyncio.sleep(3)
#     exploded_targets = random.randint(10, 80)
#     civilian_killed = random.randint(1, 30)
#     money = 10000
#     for i in range(civilian_killed):
#         money -= 30
#         print(f"Subtracting {money}")
#     for i in range(exploded_targets):
#         money += 15
#     print(f"Adding {money}")
#     total_money = money
#     await interaction.edit_original_response(content=f"Deploying Drone...")
#     await asyncio.sleep(5)
#     await interaction.edit_original_response(content=f"Targets have been spotted, making quick work of them")
#     await asyncio.sleep(5)
#     await interaction.edit_original_response(content=f"Neutralized {exploded_targets} targets, but {civilian_killed} civilians were killed. You have earned ${total_money}")

#     postcurse.execute("UPDATE currency SET money = money + %s WHERE user_id = %s", (total_money, str(interaction.user.id)))



# @work_commands.command(
#     name="blacksmith",
#     description="Time to forge some cool stuff"
# )

# @can_work('blacksmith')
# @caliente.event
# async def blacksmith(interaction: discord.Interaction):
#     blades = ["silver", "gold", "bronze", "iron", "steel"]
#     hilts = ["wooden", "leather", "metal", "bone"]
#     handles = ["wooden", "leather", "metal", "bone"]
#     crossguards = ["wooden", "leather", "metal", "bone"]

#     sword = {
#         "blade": random.choice(blades),
#         "hilt": random.choice(hilts),
#         "handle": random.choice(handles),
#         "crossguard": random.choice(crossguards)
#     }

#     await interaction.response.send_message("Forging a sword...", ephemeral=True)
#     await asyncio.sleep(10)
#     await interaction.edit_original_response(content="Polishing the sword...")
#     await asyncio.sleep(5)
#     await interaction.edit_original_response(content=f"You have created a sword with a {sword['blade']} blade, {sword['hilt']} hilt, {sword['handle']} handle, and {sword['crossguard']} crossguard, you have earned $2000")

#     postcurse.execute("UPDATE currency SET money = money + 2000 WHERE user_id = %s", (str(interaction.user.id),))
# @work_commands.command(
#     name="coalminer",
#     description="Its 2024, why are you still mining coal?"
# )

# @can_work('coalminer')
# @caliente.event
# async def coalminer(interaction: discord.Interaction):
#     postcurse.execute("UPDATE currency SET money = money + 300 WHERE user_id = %s", (str(interaction.user.id),))
#     await interaction.response.send_message("Mining some coal...", ephemeral=True)
#     await asyncio.sleep(10)
#     await interaction.edit_original_response(content="Picking up the last piece of coal...")
#     await asyncio.sleep(5)
#     await interaction.edit_original_response(content="'Well, bless my soul' says the boss man as he hands you your pay of $300")

# @work_commands.command(
#     name="farm",
#     description="A farmers sanctuary, time to move some haybails"
# )
# @can_work('farmer')
# @caliente.event

# async def farm(interaction: discord.Interaction):
#     postcurse.execute("UPDATE currency SET money = money + 1200 WHERE user_id = %s", (str(interaction.user.id),))   
#     await interaction.response.send_message("After a long day of work, you have earned $1200", ephemeral=True)

# @work_commands.command(
#     name="accountant",
#     description="Time to crunch some numbers"
# )

# @app_commands.checks.cooldown(1, 1)
# @can_work('accountant')
# @caliente.event
# async def accountant(interaction: discord.Interaction):
#     await interaction.response.send_modal(accounting.AccountingMath())
# tree.add_command(work_commands)
# """Economy Commands"""
# economy = app_commands.Group(name="eco", description="A bunch of economy commands")
# job = app_commands.Group(name="job", description="Odd jobs to earn money")

# @job.command(
#     name="quit",
#     description="Quit your current job"
# )

# @caliente.event
# async def quit(interaction: discord.Interaction):
#     class JobQuitView(discord.ui.View):
#         def __init__(self):
#             super().__init__()
#         @discord.ui.button(label="Yes", style=discord.ButtonStyle.green)
#         async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
#             postcurse.execute("UPDATE currency SET job = NULL WHERE user_id = %s", (str(interaction.user.id),))
#             button.disabled = True
#             await interaction.response.send_message("You have quit your job", ephemeral=True)
#         @discord.ui.button(label="No", style=discord.ButtonStyle.red)
#         async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
#             button.disabled = True
#             await interaction.response.send_message("Action canceled", ephemeral=True)
#     postcurse.execute("UPDATE currency SET job = NULL WHERE user_id = %s", (str(interaction.user.id),))
#     await interaction.response.send_message("Are you sure you wish to quit your job?", view=JobQuitView(), ephemeral=True)

# @job.command(
#     name="apply",
#     description="Apply for a job"
# )

# @caliente.event

# async def apply(interaction: discord.Interaction):
#     with open("Gamble/jobs.json") as f:
#         jobs = json.load(f)
#     regular_jobs = jobs["Regular Jobs"]
#     premium_jobs = jobs["Premium Jobs"]
#     postcurse.execute("SELECT job FROM currency WHERE user_id = %s AND job IS NOT NULL AND job != ''", (str(interaction.user.id),))
#     job = postcurse.fetchone()
#     if job is not None:
#         await interaction.response.send_message("You already have a job, quit your job to apply for a new one", ephemeral=True)
#         return
#     postcurse.execute("SELECT user_id FROM premium_users WHERE user_id = %s", (str(interaction.user.id),))
#     premium_user = postcurse.fetchone()
#     postcurse.execute("SELECT user_id FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()
#     if result is None:
#         await interaction.response.send_message("I see your enthusiasm, but you need to start your economic journey first. Do /eco start", ephemeral=True)
#         return
#     class JobDropdown(discord.ui.Select):
#         def __init__(self):
#             options = []
#             for job in regular_jobs:
#                 options.append(discord.SelectOption(label=f"{job['details']['displayname']} - Regular Job", value=job["job_name"]))
#             if premium_user is not None:
#                 for job in premium_jobs:
#                     options.append(discord.SelectOption(label=f"{job['details']['displayname']} - Premium Job", value=job["job_name"]))
#             super().__init__(placeholder="Select a job", options=options)

#         async def callback(self, interaction: discord.Interaction):
#             selected_job = self.values[0]
#             if selected_job == "coalminer":
#                 await interaction.response.send_modal(job_modals.CoalMinerJob())
#             elif selected_job == "podcasthost":
#                 await interaction.response.send_modal(job_modals.PodCastHostJob())
#             elif selected_job == "farmer":
#                 await interaction.user.send("You are now a farmer! Goodluck getting by with your new job")
#             elif selected_job == "assassian":
#                 await interaction.user.send("You are now an assassian! Dont get caught...")
#             elif selected_job == "accountant":
#                 await interaction.response.send_modal(job_modals.AccountingJob())
#             elif selected_job == "droneoperator":
#                 await interaction.response.send_modal(job_modals.DroneOperatorJob())
#             elif selected_job == "militaryengineer":
#                 await interaction.response.send_modal(job_modals.MilitaryEngineer())
#             elif selected_job == "blacksmith":
#                 await interaction.response.send_modal(job_modals.BlackSmithJob())  
#             postcurse.execute("UPDATE currency SET job = %s WHERE user_id = %s", (selected_job, str(interaction.user.id)))
#     class DropdownView(discord.ui.View):
#         def __init__(self):
#             super().__init__()
#             self.add_item(JobDropdown())
#     await interaction.response.send_message("Select a job to apply for", view=DropdownView())
# tree.add_command(job)
# @tree.command(
#     name="listjobs",
#     description="List the avaliable Jobs"
# )

# @caliente.event

# async def listjobs(interaction: discord.Interaction):
#     with open("Gamble/jobs.json") as f:
#         jobs = json.load(f)
#     regular_jobs = jobs["Regular Jobs"]
#     premium_jobs = jobs["Premium Jobs"]
#     class Jobs(discord.ui.View):
#         def __init__(self):
#             super().__init__(timeout=None)

#         @discord.ui.button(label="Regular Jobs", style=discord.ButtonStyle.grey)
#         async def regular_jobs(self, interaction: discord.Interaction, button: discord.ui.Button):
#             embed = discord.Embed(title="Regular Jobs", description="List of regular jobs", color=0x00FF00)
#             for job in regular_jobs:
#                 embed.add_field(name=job["details"]["displayname"], value=f"Salary: ${job['details']['payperday']} per day", inline=False)
#             await interaction.response.edit_message(embed=embed)
            
#         @discord.ui.button(label="Premium Jobs", style=discord.ButtonStyle.grey)
#         async def premium_jobs(self, interaction: discord.Interaction, button: discord.ui.Button):
#             embed = discord.Embed(title="Premium Jobs", description="List of premium jobs", color=0x00FF00)
#             for job in premium_jobs:
#                 embed.add_field(name=job["details"]["displayname"], value=f"Salary: ${job['details']['payperday']} per day", inline=False)
#             await interaction.response.edit_message(embed=embed)

#     await interaction.response.send_message(view=Jobs())
# def load_shop_items():
#     shop_query = sql.SQL("SELECT item_name FROM shop_items")
#     postcurse.execute(shop_query)
#     items = postcurse.fetchall()
#     return [item[0] for item in items]  # Unpack the tuples

# items = load_shop_items()

# async def shop_autocomplete(interaction: discord.Interaction, current: str):
#     return [discord.app_commands.Choice(name=item, value=item) for item in items if current.lower() in item.lower()]
# @economy.command(
#     name="leaderboard",
#     description="Shows who is the richest on the global leaderboard"
# )

# @caliente.event

# async def leaderboard(interaction: discord.Interaction):
#     get_leaderboard = sql.SQL("SELECT user_name, money FROM currency ORDER BY money DESC LIMIT 10")
#     postcurse.execute(get_leaderboard)
#     leaderboard = postcurse.fetchall()
#     embed = discord.Embed(title="Leaderboard", description="The richest users", color=0x00FF00)
#     for index, user in enumerate(leaderboard):
#         embed.add_field(name=f"{index + 1}. {user[0]}", value=f"Balance: {user[1]} currency", inline=False)
#     embed.set_footer(text="The leaderboard is updated every 5 minutes")
#     await interaction.response.send_message(embed=embed, ephemeral=True)

# @economy.command(
#     name="buy",
#     description="Buys an item from the shop"
# )   

# @app_commands.describe(item="Choose an item to buy")
# @app_commands.autocomplete(item=shop_autocomplete)

# @caliente.event
# async def buy(interaction: discord.Interaction, item: str, amount: int = 1):
#     item_value = items_service.get_item_value(item)
#     items_service.buy_item(interaction.user.id, item, amount)
#     if amount < 0:
#         await interaction.response.send_message("You cannot buy a negative amount", ephemeral=True)
#         return
#     await interaction.response.send_message(f"Bought {amount} {item} for {item_value} currency", ephemeral=True)

# @economy.command(
#     name="shop",
#     description="Gives the user a list of items from the shop"
# )
# @caliente.event

# async def shop(interaction: discord.Interaction):
#     get_items = sql.SQL("SELECT item_name, item_cost, item_quantity FROM shop_items")
#     postcurse.execute(get_items)
#     items = postcurse.fetchall()
#     embed = discord.Embed(title="Shop", description="Buy items from the shop", color=0x00FF00)
#     for item in items:
#         embed.add_field(name=item[0], value=f"Price: {item[1]} currency, quantity: {item[2]}", inline=False)
#     await interaction.response.send_message(embed=embed, ephemeral=True)

# @shop.error
# async def on_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, ValueError):
#         await interaction.response.send_message("This item doesn't exist or it is out of stock")




# @economy.command(
#     name="sell",
#     description="Sells an item for a certain amount of currency"
# )

# @app_commands.describe(item="Choose an item to sell")
# @app_commands.autocomplete(item=item_autocomplete)
# @caliente.event

# async def sell(interaction: discord.Interaction, item: str, amount: int = 1):
#     await interaction.response.defer(thinking=True, ephemeral=True)
#     item_value = items_service.get_item_value(item)
#     items_service.sell_item(interaction.user.id, item, amount)
#     if amount < 0:
#         await interaction.followup.send("You cannot sell a negative amount", ephemeral=True)
#         return
#     await interaction.followup.send(f"Sold {amount} {item} for {item_value} currency", ephemeral=True)
# @sell.error
# async def on_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, discord.errors.HTTPException) and error.code == 50035:
#         print("Ignoring")
#         return
#     if isinstance(error, ValueError):
#         await interaction.response.send_message("This item doesn't exist in your inventory or you don't have enough of it", ephemeral=True)
#     # Handle other errors here
# @economy.command(
#     name="balance",
#     description="Returns the balance of the user"
# )

# @caliente.event
# async def balance(interaction: discord.Interaction):
#     user_id = str(interaction.user.id)
#     query = sql.SQL("SELECT * FROM currency WHERE user_id = %s")
#     postcurse.execute(query, (user_id,))
#     result = postcurse.fetchone()
#     if result is None:
#         await interaction.response.send_message("You have not started your economic journey", ephemeral=True)
#         return
#     currency = result[2]
#     await interaction.response.send_message(f"Your balance is {currency} currency", ephemeral=False)

# @economy.command(
#     name="start",
#     description="Begins your economic journey"
# )

# @caliente.event

# async def begin(interaction: discord.Interaction):
#     user_id = str(interaction.user.id)
#     postquery = sql.SQL("SELECT * FROM currency WHERE user_id = %s")
#     postcurse.execute(postquery, (user_id,))
#     result = postcurse.fetchone()
#     if result is not None:
#         await interaction.response.send_message("You have already started your economic journey", ephemeral=True)
#         return
#     class StartButton(discord.ui.View):
#         def __init__(self):
#             super().__init__(timeout=30)
#         @discord.ui.button(label="Start", style=discord.ButtonStyle.green)
#         async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
#             currency = 1000
#             user_name = interaction.user.name
#             query = sql.SQL("INSERT INTO currency (user_id, user_name, money) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO NOTHING")
#             postcurse.execute(query, (user_id, user_name, currency))
#             connector.commit()
#             await interaction.response.send_message("You have started your economic journey with 1000 currency", ephemeral=True)
#             button.disabled = True
#     await interaction.response.send_message("You are about to venture on a journey like never before. Click the button before 30 seconds, otherwise you have declined the journey.", view=StartButton())
# @economy.command(
#     name="pay",
#     description="Pays a user a certain amount of currency",
# )

# @caliente.event

# @app_commands.checks.cooldown(2, 30)

# async def pay(interaction: discord.Interaction, user: discord.User, amount: int):
#     if amount < 0:
#         await interaction.response.send_message("You cannot pay a negative amount", ephemeral=True)
#         return
#     user_id = str(interaction.user.id)
#     user_id2 = str(user.id)
#     user_name2 = user.name
#     query = sql.SQL("SELECT * FROM currency WHERE user_id = %s")
#     postcurse.execute(query, (user_id,))
#     result = postcurse.fetchone()
#     if result is None:
#         await interaction.response.send_message("You have not started your economic journey", ephemeral=True)
#         return
#     query2 = sql.SQL("SELECT * FROM currency WHERE user_id = %s")
#     postcurse.execute(query2, (user_id2,))
#     result2 = postcurse.fetchone()
#     if result2 is None:
#         await interaction.response.send_message("The user you are trying to pay has not started their economic journey", ephemeral=True)
#         return
#     if result[2] < amount:
#         await interaction.response.send_message("You do not have enough currency to pay this user", ephemeral=True)
#         return
#     query3 = sql.SQL("UPDATE currency SET money = money + %s WHERE user_id = %s")
#     postcurse.execute(query3, (amount, user_id2))
#     query4 = sql.SQL("UPDATE currency SET money = money - %s WHERE user_id = %s")
#     postcurse.execute(query4, (amount, user_id))
#     query5 = sql.SQL("UPDATE currency SET net_worth = net_worth + %s WHERE user_id = %s")
#     postcurse.execute(query5, (amount, user_id2))
#     connector.commit()
#     await interaction.response.send_message(f"You have paid {user_name2} {amount} currency", ephemeral=True)
#     await caliente.get_user(int(user_id2)).send(f"{interaction.user.name} has paid you {amount} currency")
    
# @pay.error
# async def on_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, app_commands.errors.CommandOnCooldown):
#         await interaction.response.send_message("Calm down and try again later", ephemeral=True)

# tree.add_command(economy)
"""General Purpose Commands"""
@app_commands.describe(turret="The main gun of the tank")
@app_commands.describe(engine="The engine of the tank")
@app_commands.describe(armor="The armor of the tank")
@app_commands.describe(armortype="The type of armor the tank has")
@app_commands.describe(secondary="The secondary/machine gun of the tank")
@app_commands.choices(turret=[
    app_commands.Choice(name='85mm', value='85mm'),
    app_commands.Choice(name='105mm', value='105mm'),
    app_commands.Choice(name='120mm', value='120mm')
])
@app_commands.choices(engine=[
    app_commands.Choice(name='V-2-34', value='V-2-34'),
    app_commands.Choice(name='V-2-44', value='V-2-44'),
    app_commands.Choice(name='V-2-54', value='V-2-54')
])
@app_commands.choices(armor=[
    app_commands.Choice(name='Composite', value='Composite'),
    app_commands.Choice(name='Steel', value='Steel'),
    app_commands.Choice(name='Ceramic', value='Ceramic'),
    app_commands.Choice(name='Depleted Uranium', value='Depleted Uranium')
])
@app_commands.choices(armortype=[
    app_commands.Choice(name='Reactive', value='Reactive'),
    app_commands.Choice(name='Composite', value='Composite'),
    app_commands.Choice(name='Spaced', value='Spaced'),
])
@app_commands.choices(secondary=[
    app_commands.Choice(name="M240", value="M240"),
    app_commands.Choice(name="M2 Browning", value="M2 Browning"),
    app_commands.Choice(name="Mounted Mk19 Grenade Launcher", value="Mounted Mk19 Grenade Launcher"),
    app_commands.Choice(name="Mounted M134 Minigun", value="Mounted M134 Minigun")
])


@tree.command(
    name="createtank",
    description="Creates a tank for the user"
)

@caliente.event
async def createtank(interaction: discord.Interaction, tank_name: str, turret: str, engine: str, armor: str, armortype: str, secondary: str):
    # user_id = str(interaction.user.id)
    # db = client["test"]
    # collection = db[user_id]
    # tank_data = {
    #     "tank_name": tank_name,
    #     "turret": turret,
    #     "engine": engine,
    #     "armor": armor,
    #     "armortype": armortype,
    #     "secondary": secondary
    # }
    # collection.insert_one(tank_data)
    await interaction.response.defer(thinking=True)
    await interaction.followup.send(f"Tank features: {tank_name}, {turret}, {engine}, {armor}, {armortype}, {secondary}", ephemeral=True)

@tree.command(
    name="serverinfo",
    description="Gives information about the server"
)
@app_commands.checks.cooldown(1, 5)
@caliente.event

async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    mycursor.execute("SELECT reputation FROM guild_profiles WHERE guild_id = %s", (guild.id,))
    result = mycursor.fetchone()
    embed = discord.Embed(title=f"{guild.name}", description="Server Information", color=0x00FF00)
    embed.set_thumbnail(url=guild.icon.url if guild.icon else guild.owner.avatar.url)
    embed.add_field(name="Server Owner", value=guild.owner, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Text", value=len(guild.text_channels), inline=True)
    embed.add_field(name="Voice", value=len(guild.voice_channels), inline=True)
    embed.add_field(name="Categories", value=len(guild.categories), inline=True)
    embed.add_field(name="Threads", value=len(guild.threads), inline=True)
    embed.add_field(name="Boosts", value=guild.premium_subscription_count, inline=True)
    embed.add_field(name="Server Reputation", value=result[0], inline=True)
    embed.add_field(name="Role list", value=" ".join([role.name for role in guild.roles[:10]]), inline=False)
    embed.add_field(name="Server Banner", value=guild.banner.url if guild.banner else "No banner", inline=False)
    embed.set_footer(text=f"Created at {guild.created_at.strftime('%d-%m-%Y')} - ID: {guild.id}")
    await interaction.response.send_message(embed=embed, ephemeral=False)

# @tree.command(
#     name="inventory",
#     description="Returns the inventory for the user",
# )

# @caliente.event

# async def inventory(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)
#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     items = list(collection.find())

#     if not items:
#         await interaction.followup.send("Your inventory is empty.")
#         return

#     # Define category priority
#     categories_order = ["Mythical", "Legendary", "Epic", "Rare", "Uncommon", "Common"]
#     category_priority = {category: i for i, category in enumerate(categories_order)}

#     items.sort(key=lambda x: category_priority[x["category"]])

#     ITEMS_PER_PAGE = 10

#     embeds = []
#     for i in range(0, len(items), ITEMS_PER_PAGE):
#         embed = discord.Embed(title=f"{interaction.user.name}'s Inventory", description="Sorted from Mythical to Common")
#         for item in items[i:i + ITEMS_PER_PAGE]:
#             item_name = item["item_name"]
#             item_count = item["count"]
#             embed.add_field(name=f"{item_name} - {item['category']}", value=f"Amount: {item_count}", inline=False)
#         embeds.append(embed)

#     # Pagination with interactive buttons
#     class PageTurner(discord.ui.View):
#         def __init__(self, embeds, start_page=0):
#             super().__init__()
#             self.embeds = embeds
#             self.current_page = start_page

#         @discord.ui.button(label='Previous', style=discord.ButtonStyle.grey)
#         async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
#             if self.current_page > 0:
#                 self.current_page -= 1
#                 await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

#         @discord.ui.button(label='Next', style=discord.ButtonStyle.grey)
#         async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
#             if self.current_page < len(self.embeds) - 1:
#                 self.current_page += 1
#                 await interaction.response.edit_message(embed=self.embeds[self.current_page], view=self)

#     if embeds:
#         await interaction.followup.send(embed=embeds[0], view=PageTurner(embeds))
#     else:
#         await interaction.followup.send("Your inventory is empty.")

# item_commands = app_commands.Group(name="open", description="Spend your money on items that might have value")

# @item_commands.command(
#     name="common",
#     description="$5 for a common crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def common(interaction: discord.Interaction):
#     # Query the database to get the user's current money
#     await interaction.response.defer(thinking=True)
#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()

#     # Check if the user has enough money
#     if result[0] < 5:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 5 WHERE user_id = %s", (str(interaction.user.id),))

#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Common"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Common",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Common Item!", description="Let's see what you got!", color=0xFFFFFF)
#     embed_var.add_field(name="Category", value="Common", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Common"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.command(
#     name="uncommon",
#     description="$25 for a common crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def uncommon(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)
#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()

#     # Check if the user has enough money
#     if result[0] < 25:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 5 WHERE user_id = %s", (str(interaction.user.id),))

#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Uncommon"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Uncommon",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Uncommon Item!", description="Let's see what you got!", color=0x00FF00)
#     embed_var.add_field(name="Category", value="Uncommon", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Uncommon"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.command(
#     name="rare",
#     description="250$ for a common crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def rare(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)
#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()

#     # Check if the user has enough money
#     if result[0] < 250:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 5 WHERE user_id = %s", (str(interaction.user.id),))

#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Rare"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Rare",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Rare Item!", description="Let's see what you got!", color=0x0000FF)
#     embed_var.add_field(name="Category", value="Rare", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Rare"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.command(
#     name="epic",
#     description="$1100 for a common crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def epic(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)
#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()

#     # Check if the user has enough money
#     if result[0] < 1100:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 1100 WHERE user_id = %s", (str(interaction.user.id),))

    
#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Epic"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Epic",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Epic Item!", description="Let's see what you got!", color=0xA20F0)
#     embed_var.add_field(name="Category", value="Epic", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Epic"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.command(
#     name="legendary",
#     description="$7000 for a legendary crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def legendaryitem(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)
#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()
#     # Check if the user has enough money
#     if result[0] < 7000:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 7000 WHERE user_id = %s", (str(interaction.user.id),))
#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Legendary"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Legendary",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Legendary Item!", description="Let's see what you got!", color=0xFFD700)
#     embed_var.add_field(name="Category", value="Legendary", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Legendary"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.command(
#     name="mythical",
#     description="$3900000 for a mythical crate"
# )

# @app_commands.checks.cooldown(1, 5)

# @caliente.event

# async def common(interaction: discord.Interaction):
#     await interaction.response.defer(thinking=True)

#     postcurse.execute("SELECT money FROM currency WHERE user_id = %s", (str(interaction.user.id),))
#     result = postcurse.fetchone()

#     # Check if the user has enough money
#     if result[0] < 3900000:
#         await interaction.followup.send("You don't have enough money to buy this item.")
#         return

#     # Subtract the cost of the item from the user's money
#     postcurse.execute("UPDATE currency SET money = money - 3900000 WHERE user_id = %s", (str(interaction.user.id),))
    
#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     common_items = items["Mythical"]
#     item_name, item_details = random.choice(list(common_items.items()))

#     json_data = {
#         "category": "Mythical",
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1
#     }

#     embed_var = discord.Embed(title="You got a Mythical Item!", description="Let's see what you got!", color=0xFFA500)
#     embed_var.add_field(name="Category", value="Mythical", inline=False)
#     embed_var.add_field(name="Item", value=f"{item_name} - ${item_details['value']}", inline=False)

#     user_id = str(interaction.user.id)
#     db = client["test"]
#     collection = db[user_id]

#     existing_item = collection.find_one({"item_name": item_name, "category": "Mythical"})
#     if existing_item:
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")
#     await interaction.followup.send(embed=embed_var)

# @item_commands.error
# async def on_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, app_commands.errors.CommandOnCooldown):
#         await interaction.response.send_message("You are on cooldown, try again later", ephemeral=True)


# tree.add_command(item_commands)
# @tree.command(
#     name="item",
#     description="Test your luck to get a random item",
#     guild=discord.Object(662945359244558336)
# )

# @app_commands.checks.cooldown(1, 5)
# @caliente.event
# async def item(interaction: discord.Interaction):
#     # Load item data from JSON file
#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)

#     # Setup database client
#     weights = [70, 30, 15, 5, 1, 0.5]
#     assert len(weights) == len(items.keys()), "Number of weights must match number of categories"

#     # Select a category and an item randomly based on weights
#     category = random.choices(list(items.keys()), weights=weights, k=1)[0]
#     item_name, item_details = random.choice(list(items[category].items()))

#     # Prepare data for database insertion
#     json_data = {
#         "category": category,
#         "item_name": item_name,
#         "item_details": item_details,
#         "count": 1  # Add count to the item
#     }

#     embed_var = Embed(title="You got an Item!", description="Lets see what you got!", color=0xFFFFFF)
#     colors = {
#         "Common": 0xFFFFFF,
#         "Uncommon": 0x00FF00,
#         "Rare": 0x0000FF,
#         "Epic": 0x800080,
#         "Legendary": 0xFFD700,
#         "Mythical": 0xFF4500
#     }
#     embed_var.color = colors.get(category, 0xFFFFFF)
#     embed_var.add_field(name="Category", value=category, inline=False)
#     embed_var.add_field(name="Item", value=item_name, inline=False)
#     await interaction.response.send_message(embed=embed_var)


#     # Database operations
#     db = client["test"]
#     collection = db[str(interaction.user.id)]
#     if str(interaction.user.id) not in db.list_collection_names():
#         db.create_collection(str(interaction.user.id))

#     # Check if the item already exists
#     existing_item = collection.find_one({"item_name": item_name, "category": category})

#     if existing_item:
#         # If the item exists, increment the count
#         collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#     else:
#         # If the item does not exist, insert it
#         insert_result = collection.insert_one(json_data)
#         document_id = insert_result.inserted_id

#         # Retrieve to confirm
#         inserted_data = collection.find_one({"_id": document_id})
#         print(f"Inserted data: {inserted_data}")

#         item_value = item_details["value"]
#         query = sql.SQL("UPDATE currency SET net_worth = net_worth + %s WHERE user_id = %s")
#         postcurse.execute(query, (item_value, str(interaction.user.id)))
#         # Compare the inserted and retrieved data
#         if inserted_data["item_name"] != item_name or inserted_data["category"] != category:
#             print("Error: Mismatch between inserted and retrieved data")

    
#     # Send a special message if the item is mythical
#     if category == "Mythical":
#         channel = interaction.client.get_channel(1236059362464628808)
#         await channel.send(f"{interaction.user} got a mythical item: {item_name}")

# @item.error
# async def on_command_error(interaction: discord.Interaction, error):
#     if isinstance(error, app_commands.errors.CommandOnCooldown):
#         await interaction.response.send_message("You are on cooldown, try again later", ephemeral=True)
# def getting_items():
#     with open('Gamble/items.json', 'r') as f:
#         item_dict = json.load(f)
#     return item_dict

# # Load the items dictionary from the JSON file
# items_dict = getting_items()

# # Create a list of all item names
# all_items = [item_name for category in items_dict.values() for item_name in category.keys()]

# async def item_autocomplete(interaction: discord.Interaction, current: str):
#     # Filter items based on current input
#     return [discord.app_commands.Choice(name=item, value=item) for item in all_items if current.lower() in item.lower()]



# @tree.command(
#     name="giveitem",
#     description="Gives an item to a guild",
#     guild=discord.Object(662945359244558336)
# )
# @app_commands.describe(item='Choose the item')
# @discord.app_commands.autocomplete(item=item_autocomplete)

# @caliente.event
# async def giveitem(interaction: discord.Interaction, user_id: str, item: str, amount: int = 1):
#     def get_category(item, items_dict):
#         for category, items in items_dict.items():
#             if item in items:
#                 return category
#         return None

#     db = client["test"]
#     collection = db[user_id]
#     with open('Gamble/items.json', 'r') as f:
#         items = json.load(f)
#     item_category = get_category(item, items)
#     if item_category is None:
#         await interaction.response.send_message("This item does not exist in the user inventory")
#         return
#     await interaction.response.defer(thinking=True, ephemeral=False)
#     item_details = items[item_category][item]
#     item_data = {
#         "category": item_category,
#         "item_name": item,
#         "item_details": item_details
#     }
#     for _ in range(amount):
#         existing_item = collection.find_one({"item_name": item, "category": item_category})
#         if existing_item:
#             # If the item exists, increment the count
#             collection.update_one({"_id": existing_item["_id"]}, {"$inc": {"count": 1}})
#         else:
#             # If the item does not exist, insert it
#             item_value = item_details["value"]
#             query = sql.SQL("UPDATE currency SET net_worth = net_worth + %s WHERE user_id = %s")
#             postcurse.execute(query, (item_value, user_id))
#             item_data["count"] = 1
#             collection.insert_one(item_data)
#     embed_var = discord.Embed(title="Item Given", description=f"{item} has been given to {caliente.get_user(int(user_id))} {amount} times")
#     await interaction.followup.send(embed=embed_var)
@tree.command(
    name="help",
    description="Gives you some help on how to get started"
)

@caliente.event
async def help(interaction: discord.Interaction):
    class HelpView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)
        @discord.ui.button(label="Commands", style=discord.ButtonStyle.blurple)
        async def commands(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Commands", description="You can find my list of commands by doing the / and looking at my pfp in the list of commands")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Moderation", style=discord.ButtonStyle.blurple)
        async def moderation(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Moderation", description="Bot-Bot is fitted with some basic moderation commands like ban, kick, mute and even logging. Logging is used when you execute our moderation commands. More options will be added soon.")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Helldiver Commands", style=discord.ButtonStyle.blurple)
        async def helldiver(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Helldiver Commands", description="I have some helldiver commands that can get accurate information for the planets and the galaxy by doing /getplanetstats or /galaxystats")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Weather", style=discord.ButtonStyle.blurple)
        async def weather(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Weather", description="If you need weather information and you are on discord, you can use /weather to get the latest weather information")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="General Purpose", style=discord.ButtonStyle.blurple)
        async def general(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="General Purpose", description="Wanna get some information on a user? Use /userinfo")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Feedback", style=discord.ButtonStyle.blurple)
        async def suggestions(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Feedback", description="Have any reports or suggestions? Use /feed")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Using AI", style=discord.ButtonStyle.blurple)
        async def ai(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Using AI", description="This bot is fitted with the latest version of the google gemini api. You can use /gemini to get a freeform response. Keep in mind this ai doesn't always give accurate results")
            await interaction.response.edit_message(embed=embed_var)
        @discord.ui.button(label="Join our discord", style=discord.ButtonStyle.blurple)
        async def support(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed_var = discord.Embed(title="Join our discord", description="Join our discord server to get the latest updates and to get help with the bot", url="https://discord.gg/u2YBbHjJRh")
            await interaction.response.edit_message(embed=embed_var)
    embed_var = discord.Embed(title="Help", description="Some help to get you started")
    await interaction.response.send_message(view=HelpView(), embed=embed_var)

@tree.command(
    name="feedback",
    description="Sends feedback to the bot developers"
)

@app_commands.describe(feedback="The stuff you want to send")
@app_commands.checks.cooldown(1, 3600)

@caliente.event

async def botsuggestions(interaction: discord.Interaction, feedback: str):
    channel_id = 662945428806828033
    channel = caliente.get_channel(channel_id)  
    if channel is not None:
        embed_var = discord.Embed(title="New Suggestion", color=discord.Color.green())
        embed_var.add_field(name="Feedback", value=feedback, inline=False)
        embed_var.add_field(name="User", value=interaction.user, inline=False)
        embed_var.add_field(name="Guild", value=interaction.guild, inline=False)
        await interaction.response.send_message("feedback sent.")
        await channel.send(embed=embed_var)
        try:
            with open('suggestions.json', 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = {"Suggestions": {}}
        suggestion_id = str(uuid.uuid4())
        data["Suggestions"][suggestion_id] = feedback

        with open('suggestions.json', 'w') as f:
            json.dump(data, f, indent=4)
    else:
        print("New suggestion, check the json!")
@botsuggestions.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"You have already sent feedback. Try again later", ephemeral=True)
@tree.command(
    name="removesuggestion",
    description="Removes a suggestion from the list",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def removesuggestion(interaction: discord.Interaction, suggestion_id: str):
    with open('suggestions.json', 'r') as f:
        data = json.load(f)
    if suggestion_id not in data["Suggestions"]:
        await interaction.response.send_message("Suggestion not found.")
        return
    del data["Suggestions"][suggestion_id]
    with open('suggestions.json', 'w') as f:
        json.dump(data, f, indent=4)
    await interaction.response.send_message("Suggestion removed.")

@tree.command(
        name="gaytest",
        description="Tests how gay someone is",
        guild=discord.Object(662945359244558336)
)

@caliente.event

async def gaytest(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "gaytest", limit=5, per=5):
        await interaction.response.send_message("CALM DOWN IF IT SAYS YOU'RE GAY THEN YOU'RE GAY", ephemeral=True)
        return

    await interaction.response.defer(thinking=True, ephemeral=False)
    mycursor.execute("SELECT * FROM femboys WHERE user_id = %s", (str(user_id),))
    femboys = mycursor.fetchall()

    if femboys:
        await interaction.followup.send("YOU ARE GAY. YOU ARE A CONFIRMED FEMBOY. YOU ARE THE GAYEST OF THEM ALL, 100% GAY YOU ARE A FEMBBOY")
        return

    random_number = random.randint(0, 100)
    if random_number == 100:
        print("Someone got 100% on the gay scale")
    if random_number == 0:
        await interaction.followup.send("Wow you are totally straight with a 0% gayness")
    elif random_number < 10:
        await interaction.followup.send(f"You're pretty straight but a tiny bit zesty: {random_number}%")
    elif random_number < 30:
        await interaction.followup.send(f"Might be zesty at times but you're still kind of straight: {random_number}%")
    elif random_number < 49:
        await interaction.followup.send(f"You might ask to kiss the homies tonight but still have some straightness left: {random_number}%")
    elif random_number == 50:
        await interaction.followup.send("You are bisexual")
    elif random_number < 70:
        await interaction.followup.send(f"You're probably hiding yourself in the closet: {random_number}%")
    elif random_number < 90:
        await interaction.followup.send(f"You're one of the chill gays I can tell you that: {random_number}%")
    elif random_number < 100:
        await interaction.followup.send(f"Holy shit you are taking it up there are you? {random_number}%")
        


@tree.command(
        name="userinfo",
        description="Returns information about the user"
)

@caliente.event

async def userinfo(interaction: discord.Interaction, user: discord.Member = None):
    if user is None:
        user = interaction.user
    user_id = interaction.user.id
    role_names = ', '.join([role.name for role in user.roles])
    getting_balance = sql.SQL("SELECT money FROM currency WHERE user_id = %s")
    postcurse.execute(getting_balance, (str(user_id),))
    result1 = postcurse.fetchone()

    if result1 is None:
        balance = "No balance"
    else:
        balance = result1
    if "everyone" in role_names:
        role_names = role_names.replace("@everyone", "")
    
    if not check_rate_limit(user_id, "userinfo", 5, 5):
        await interaction.response.send_message("You're doing that too often. Please wait a moment before trying again.", ephemeral=True)
        return
    embed_var = discord.Embed(title=f"User information for {user}", color=discord.Color.blue())
    embed_var.add_field(name="User name", value=user.name, inline=True)
    embed_var.add_field(name="Display name", value=user.display_name, inline=True)
    embed_var.add_field(name="User created at", value=user.created_at.strftime('%d-%m-%Y'), inline=True)
    embed_var.add_field(name="Balance", value=balance, inline=True)
    embed_var.add_field(name="Roles", value=", ".join([role.name for role in user.roles[:10]]), inline=True)
    embed_var.set_footer(text=f"Joined at {user.joined_at.strftime('%d-%m-%Y')} - ID: {user.id}")

    embed_var.set_thumbnail(url=user.avatar)
    await interaction.response.send_message(embed=embed_var)

@tree.command(
        name="botinfo",
        description="Gives information about the bot"
)

@app_commands.checks.cooldown(1, 5)
@caliente.event

async def botinfo(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    await interaction.followup.send(f"Bot-Bot, A mutlipurpose, customizable bot\nCreated By Lightning\nThis bot uitlizes the discord.py Library, being able to easily use commands with amazing and fast speed.\nThis bot is constantly being updated with more to come!\nTo check the latest updates. do /getupdate", ephemeral=False)
@botinfo.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message("You are on cooldown, try again later", ephemeral=True)
@tree.command(
    name="getupdate",
    description="Returns the latest update from the bot"
)

@caliente.event

async def getupdate(interaction: discord.Interaction):
    with open("current_update.txt") as f:
        update = f.read()
    await interaction.response.send_message(f"Current update: {update}")

@tree.command(
    name="ping",
    description="Returns the latency between discord and the bot"
)

@caliente.event

async def ping(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=False)
    discord_latency = (datetime.datetime.now(datetime.timezone.utc) - interaction.created_at).total_seconds() * 1000
    await interaction.followup.send(f"Pong! Bot latency: {round(caliente.latency * 1000)}ms, Discord Latency: {round(discord_latency)}ms", ephemeral=False)

@tree.command(
    name="serversuggestion",
    description="Sends a suggestion to the server"
)

@app_commands.checks.cooldown(1, 3600)

@caliente.event
async def serversuggestion(interaction: discord.Interaction, suggestion: str):
    channel = "SELECT suggestions_channel FROM guilds WHERE guild_id = %s"
    guild_id = str(interaction.guild.id)
    mycursor.execute(channel, (guild_id,))
    result = mycursor.fetchone()
    if result is None:
        await interaction.response.send_message("No suggestion has been set, if you are an admin, do /setsuggestionschannel to set a suggestion channel")
        return
    channel = caliente.get_channel(int(result[0]))
    if channel is None:
        await interaction.response.send_message("Channel not found")
        return
    embed_var = discord.Embed(title="New Suggestion", color=discord.Color.green())
    embed_var.add_field(name="Suggestion", value=suggestion, inline=False)
    embed_var.add_field(name="User", value=interaction.user, inline=False)
    message = await channel.send(embed=embed_var)
    await message.add_reaction("👍")
    await message.add_reaction("👎")
    await interaction.response.send_message("Suggestion sent.")
@serversuggestion.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"You are doing that too often, wait an hour before trying again later", ephemeral=True)
    
    await interaction.response.send_message("Suggestion sent.")

"""Administrative Commands"""
random_number = random.randint(0, 100)
@tree.command(
    name="backup",
    description="Backs up your server info to a secure location"
)



@app_commands.checks.has_permissions(administrator=True)
@caliente.event
async def backup(interaction: discord.Interaction, backup_name: str = "backup"):
    class BackupView(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=180)
        @discord.ui.button(label="Backup", style=discord.ButtonStyle.green)
        async def backup(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Backing up your server", ephemeral=True)
            with open(f"{backup_name}-{interaction.guild.id}.json", "w") as f:
                roles_with_stuff = []
                for role in interaction.guild.roles:
                    if role.is_bot_managed() or role.is_default():
                        roles_with_stuff.append(role.id)


                channels = {}
                roles = {}
                categories = {}
                threads = {}
                sorted_categories = sorted(interaction.guild.categories, key=lambda category: category.position)

                for category in sorted_categories:
                    # If the category is not in the categories dictionary, add it
                    if category.id not in categories:
                        categories[str(category.id)] = {
                            "name": category.name,
                            "channels": {}
                        }

                    # Sort channels in the category by position
                    sorted_channels = sorted(category.channels, key=lambda channel: channel.position)

                    for channel in sorted_channels:
                        channel_data = {
                            "name": channel.name,
                            "type": str(channel.type)
                        }

                        # Add the channel data to the category
                        categories[str(category.id)]["channels"][str(channel.id)] = channel_data
                    else:
                        # If the channel doesn't have a category, add it to the channels dictionary
                        channels[str(channel.id)] = channel_data

                for role in interaction.guild.roles:
                    if role.id not in roles_with_stuff and role.position < interaction.guild.me.top_role.position:
                        roles[str(role.id)] = {
                            "name": role.name if role.name != "@everyone" else "everyone",
                            "permissions": role.permissions.value
                        }

                for thread in interaction.guild.threads:
                    threads[str(thread.id)] = {
                        "name": thread.name
                    }

                backup_data = {
                    "guild_name": interaction.guild.name,
                    "roles": roles,
                    "categories": categories,
                    "threads": threads
                }
                
                guild_backup = guild_backups[str(interaction.guild.id)]
                
                collection = guild_backup[backup_name]
                collection.insert_one(backup_data)


            await interaction.followup.send("Backup complete", ephemeral=True)
    embed=discord.Embed(title="Bot-Bot Backup")
    embed.add_field(name="What will be backed up", value="Channels, guild name, roles, categories, threads, permissions", inline=False)
    embed.add_field(name="What will not be backedup", value="Member data, what roles they had, messages", inline=True)
    await interaction.response.send_message(embed=embed, view=BackupView())

@tree.command(
    name="loadbackup",
    description="Loads a backup of the server"
)

@app_commands.checks.has_permissions(administrator=True)
@caliente.event

async def loadbackup(interaction: discord.Interaction, backup_name: str = None):
    await interaction.response.send_message("This is a destructive operation. Please say 'load backup' to confirm", ephemeral=True)

    await caliente.wait_for("message", check=lambda message: message.author == interaction.user and message.content.lower() == "load backup")   

    # Get the database (guild ID)
    guild_backup = guild_backups[str(interaction.guild.id)]

    # Get the collection (backup name)
    collection = guild_backup[backup_name]

    # Find the backup
    backup = collection.find_one()
    if backup is None:
        await interaction.response.send_message("Backup not found", ephemeral=True)
        return

    # Delete existing channels, roles, categories, and threads
    for channels in interaction.guild.channels:
        await channels.delete()
    for roles in interaction.guild.roles:
        if roles.position >= interaction.guild.me.top_role.position:
            print("This role is higher than my top role, skipping")
        if roles.is_default():
            print(f"Skipping role {roles.name}")
            continue
        if roles.is_bot_managed():
            print(f"Skipping role {roles.name}")
            continue
        await roles.delete()
        print(f"Deleted role {roles.name}")
    for categories in interaction.guild.categories:
        await categories.delete()
    for threads in interaction.guild.threads:
        await threads.delete()

    # Send a message to the guild owner
    await interaction.guild.owner.send("Loading backup, this may take a while.")

    # Create categories and channels
    for category_id, category_data in backup["categories"].items():
        new_category = await interaction.guild.create_category(category_data["name"])
        for channel_id, channel_data in category_data["channels"].items():
            if channel_data["type"] == "text":
                await new_category.create_text_channel(channel_data["name"])
            elif channel_data["type"] == "voice":
                await new_category.create_voice_channel(channel_data["name"])

    # Create roles
    for role_id, role_data in backup["roles"].items():
        await interaction.guild.create_role(name=role_data["name"], permissions=discord.Permissions(int(role_data["permissions"] if role_data["permissions"] else 0)))

    # Create threads
    for thread_id, thread_data in backup["threads"].items():
        await interaction.guild.create_text_channel(thread_data["name"], thread=True)

    await interaction.user.send("Loading backup")
            
"""Moderation Commands"""
@tree.command(
    name="setsuggestionchannel"
)
@app_commands.checks.has_permissions(administrator=True)
@caliente.event

async def setsuggestionchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    guild_id = str(interaction.guild.id)
    sql = "UPDATE guilds SET suggestions_channel = %s WHERE guild_id = %s"
    val = (str(channel.id), guild_id)
    mycursor.execute(sql, val)
    guild_db.commit()
    await interaction.response.send_message(f"Suggestion channel set to {channel.mention}")

@setsuggestionchannel.error

async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You must have administrator to do this")
@tree.command(
    name="removetimeout",
    description="Removes the timeout from the user"
)

@has_permissions()
@caliente.event
async def removetimeout(interaction: discord.Interaction, user: discord.Member):
    await interaction.response.send_message(f"User {user} has been removed from timeout.")


@removetimeout.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"You are doing that too often, wait a minute before trying again", ephemeral=True)
@tree.command(
    name="timeout",
    description="Times out the user for a certain amount of time"
)
@has_permissions()
@app_commands.checks.cooldown(5, 1)

@caliente.event
async def timeout(interaction: discord.Interaction, member: discord.Member, time: str):
    #await interaction.response.defer(thinking=True, ephemeral=False)

    time_dict = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    try:
        time_unit = time[-1]
        time_value = int(time[:-1])
        time_in_seconds = time_value * time_dict[time_unit]
    except (KeyError, ValueError):
        await interaction.followup.send("Invalid time format. Please use s, m, h, or d.")
        return
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to timeout this user.", ephemeral=True)

    timeout_duration = timedelta(seconds=time_in_seconds)
    await member.timeout(timeout_duration, reason="Timed out by a moderator", atomic=True)

    await interaction.response.send_message(f"Timed out user for {time}")

@timeout.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message(f"You are doing that too often, wait a minute before trying again", ephemeral=True)

@tree.command(
        name="setmuterole",
        description="Sets the mute role for the bot"
)

@app_commands.checks.has_permissions(administrator=True)
@app_commands.checks.has_permissions(manage_guild=True)

@caliente.event
async def setmuterole(interaction: discord.Interaction, role: discord.Role):
    if not admin_permissions(interaction.user) or not interaction.guild.owner:
        await interaction.response.send_message("This command can only be used in a server by admins", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)
    sql = "UPDATE guilds SET mute_role = %s WHERE guild_id = %s"
    val = (str(role.id), guild_id)
    mycursor.execute(sql, val)
    guild_db.commit()

    await interaction.response.send_message(f"Mute role set to {role.name}")
@setmuterole.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")

@tree.command(
        name="unmute",
        description="Unmutes the user"
)
@has_permissions()
@caliente.event

async def unmute(interaction: discord.Interaction, user: discord.Member):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "unmute", 1, 5):
        await interaction.response.send_message("Chill out, they will be unmuted if you calm down", ephemeral=True)
        return
    if not (moderator_permissions(interaction.user) or not admin_permissions(interaction.user) or not interaction.guild.owner):
        await interaction.response.send_message("This command can only be used in a server by users with Manage Server permission.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)

    # Query the mute role from the MySQL database
    mycursor.execute(f"SELECT mute_role FROM guilds WHERE guild_id = {guild_id}")
    mute_role_id = mycursor.fetchone()[0]

    if mute_role_id is None:
        await interaction.response.send_message("Mute role not found.")
        return
    mute_role = interaction.guild.get_role(int(mute_role_id))
    if mute_role is None:
        await interaction.response.send_message("Role with given ID not found.")
        return
    if mute_role.position >= interaction.guild.me.top_role.position:
        await interaction.response.send_message("The mute role is higher than my role. ", file="/Gifs/tutorial1.gif")
        return
    try:
        if mute_role not in user.roles:
            await interaction.response.send_message("User is not muted.")
            return
        await user.remove_roles(mute_role)
        await interaction.response.send_message(f"{user} has been unmuted.")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to unmute this user.", ephemeral=True)

@unmute.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
@tree.command(
    name="mute",
    description="Mutes the user until you run /unmute"

)

@has_permissions()

@caliente.event
async def mute(interaction: discord.Interaction, user: discord.Member):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "mute", 5, 5):
        await interaction.response.send_message("Calm down, its not like you're getting raided", ephemeral=True)
        return
    if not (moderator_permissions(interaction.user) or not admin_permissions(interaction.user) or not interaction.guild.owner):
        await interaction.response.send_message("This command can only be used in a server by users with Manage Server permission.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)

    # Query the mute role from the MySQL database
    mycursor.execute(f"SELECT mute_role FROM guilds WHERE guild_id = {guild_id}")
    mute_role_id = mycursor.fetchone()[0]

    if mute_role_id is None:
        await interaction.response.send_message("Mute role not found.")
        return
    mute_role = interaction.guild.get_role(int(mute_role_id))
    if mute_role is None:
        await interaction.response.send_message("Role with given ID not found.")
        return
    if mute_role.position >= interaction.guild.me.top_role.position:
        with open("Gifs/tutorial1.gif", "rb") as f:
            await interaction.response.send_message("The mute role is higher than my role.", file=discord.File(f))  
        return
    try:
        # Attempt to add the mute role to the user
        await user.add_roles(mute_role) 
        await interaction.response.send_message(f"{user} has been muted.")
    except discord.Forbidden:
        await interaction.response.send_message("I don't have permission to mute this user.", ephemeral=True)
@mute.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
@tree.command(
        name="setlogchannel",
        description="Sets the logging channel for the bot"
)
@app_commands.checks.has_permissions(administrator=True)
@app_commands.checks.has_permissions(manage_guild=True)
@caliente.event
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    user_id = interaction.user.id
    interaction.user.guild_permissions.manage_guild
    if not check_rate_limit(user_id, "setlogchannel", 1, 5):
        await interaction.response.send_message("You are gonna confuse me if you keep doing this", ephemeral=True)
        return
    if not (moderator_permissions(interaction.user) or not admin_permissions(interaction.user) or not interaction.guild.owner):
        await interaction.response.send_message("This command can only be used in a server by users with Manage Server permission.", ephemeral=True)
        return
    guild_id = str(interaction.guild.id)

    # Update the logging channel in the MySQL database
    sql = "UPDATE guilds SET channel_id = %s WHERE guild_id = %s"
    val = (str(channel.id), guild_id)
    mycursor.execute(sql, val)
    guild_db.commit()

    await interaction.response.send_message(f"Logging channel set to {channel.mention}")
    print(f"Logging channel set to {channel.mention}")
@setlogchannel.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
@tree.command(
    name="ban",
    description="Bans the mentioned user"
)
@has_permissions()
 
@caliente.event

async def ban(interaction: discord.Interaction, user: discord.User, reason: str="No reason given"):
    #mycursor.execute(f"SELECT channel_id FROM guilds WHERE guild_id = {interaction.guild.id}")
    #logging_channel_id = mycursor.fetchone()[0]
    #logging_channel = interaction.guild.get_channel(int(logging_channel_id))
    # embed_var = discord.Embed(title="Banned")
    # embed_var.set_author(name="Bot-Bot Logs")
    # embed_var.add_field(name="User", value=user, inline=True)
    # embed_var.add_field(name="Moderator", value=interaction.user, inline=True)
    # embed_var.add_field(name="Reason", value=reason, inline=False)
    # embed_var.set_footer(text=f"{datetime.datetime.now()} | Executed by: {interaction.user.id}")
    if interaction.guild.me.top_role.position <= user.top_role.position:
        await interaction.response.send_message("This users role is higher than me, I cannot ban them.")
        return
    await interaction.guild.ban(user, reason=reason)
    # if logging_channel is None:
    #     print("Logging channel not found but user was banned")
    # else:
    #     await logging_channel.send(embed=embed_var)
    # Attempt to ban the user
    await interaction.response.send_message(f"User {user} has been banned for reason: {reason}")
    print(f"{interaction.message.author} has banned {user} from guild: {interaction.guild}")
    # if logging_channel is None:
    #     print("Logging channel was not found but user was banned")
    # else:
    #     await logging_channel.send(embed=embed_var)

@ban.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
    if isinstance(error, discord.Forbidden):
        await interaction.response.send_message("I do not have permissions to ban this user")
@tree.command(
        name="kick",
        description="Kicks the mentioned user"
)
@has_permissions()

@caliente.event
async def kick(interaction: discord.Interaction, user: discord.User, reason: str="No reason given"):
    mycursor.execute(f"SELECT channel_id FROM guilds WHERE guild_id = {interaction.guild.id}")
    logging_channel_id = mycursor.fetchone()[0]
    logging_channel = interaction.guild.get_channel(int(logging_channel_id))
    embed_var = discord.Embed(title="Kicked")
    embed_var.set_author(name="Bot-Bot Logs")
    embed_var.add_field(name="User", value=user, inline=True)
    embed_var.add_field(name="Moderator", value=interaction.user, inline=True)
    embed_var.add_field(name="Reason", value=reason, inline=False)
    embed_var.set_footer(text=f"{datetime.datetime.now()} | Executed by: {interaction.user.id}")
    await interaction.guild.kick(user, reason=reason)
    if logging_channel is None:
        print("Logging channel not found but user was kicked")
    else:
        await logging_channel.send(embed=embed_var)
    # Attempt to ban the user
    await interaction.response.send_message(f"{user} was kicked")
    print(f"{interaction.message.author} has kicked {user} from guild: {interaction.guild}")
@kick.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to use this")
    if isinstance(error, discord.Forbidden):
        await interaction.response.send_message("I do not have permissions to kick this user")
"""Voice Commands"""
async def radio_autocomplete(interaction: discord.Interaction, current: str):
    mycursor.execute(f"SELECT radio_id, radio_name FROM radios")
    stations = mycursor.fetchall()

    return [discord.app_commands.Choice(name=f"{station[1]} - {station[0]}", value=station[0]) for station in stations if current.lower() in station[1].lower()]
@tree.command(
    name="disconnect",
    description="Disconnects the bot from the voice channel"
)

@caliente.event
async def disconnect(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "disconnect", 1, 5):
        await interaction.response.send_message("You're doing that too often. Please wait a moment before trying again.", ephemeral=True)
        return
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("I am not connected to a voice channel.")
        return
    await interaction.guild.voice_client.disconnect()
    await interaction.response.send_message("Disconnected from the voice channel.")
mycursor.execute('SELECT radio_id FROM radios')
station_ids = mycursor.fetchall()
# print(station_ids)

# if not station_ids:
#     raise ValueError("No station IDs found in the database")

# class StationIDs(enum.Enum):
#     {f'ID_{id_[0]}': id_[0] for id_ in station_ids}

@tree.command(
    name="radio",
    description="Plays a radio station from the radio database"
)
@app_commands.checks.cooldown(1, 5)
@app_commands.describe(stationid="The ID of the radio station to play")
@app_commands.autocomplete(stationid=radio_autocomplete)

@caliente.event

async def radio(interaction: discord.Interaction, stationid: str):
    # Check if the user is connected to a voice channel
    if interaction.user.voice is None or interaction.user.voice.channel is None:
        await interaction.response.send_message("You must be in a voice channel to use this command.")
        return
    
    # Fetch all available stations
    cursor = guild_db.cursor()
    cursor.execute(f"SELECT radio_id FROM radios")
    stations = cursor.fetchall()
    station_ids = [station[0] for station in stations]

    # Check if the given station ID exists in the list of fetched stations
    if stationid not in station_ids:
        await interaction.response.send_message("The station id was not found. To add a station, please do /addstation <station name> <station url.mp3>")
        return

    # Fetch the URL for the specified station ID
    cursor.execute('SELECT radio_url FROM radios WHERE radio_id = %s', (stationid,))
    station_url_tuple = cursor.fetchone()
    if station_url_tuple is None:
        await interaction.response.send_message("No URL found for the provided station ID.")
        return
    cursor.execute('SELECT radio_name FROM radios WHERE radio_id = %s', (stationid,))
    station_name_tuple = cursor.fetchone()
    if station_name_tuple is None:
        await interaction.response.send_message("No name found for the provided station ID.")
        return

    # Extract the name from the tuple
    station_name = station_name_tuple[0]
    # Extract the URL from the tuple
    station_url = station_url_tuple[0]

    # Connect to the voice channel and play the audio
    voice_channel = interaction.user.voice.channel
    if voice_channel is None:
        await interaction.response.send_message("You must be in a voice channel to use this command.")
        return
    voice_client = interaction.guild.voice_client
    if voice_client is not None:
        if voice_client.channel != voice_channel:
            await interaction.response.send_message("The bot is already in a different voice channel.")
            return
    else:
        voice_client = await voice_channel.connect()
    voice_client.play(discord.FFmpegPCMAudio(station_url, executable="ffmpeg"))
    await interaction.response.send_message(f"Playing radio station {station_name} ({stationid})")
@radio.error
async def on_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.errors.CommandOnCooldown):
        await interaction.response.send_message("You are doing that too often, wait 5 seconds before trying again", ephemeral=True)
    if isinstance(error, app_commands.errors.CommandInvokeError):
        await interaction.response.send_message(f"An error occurred while trying to play the radio station: {error}")

@tree.command(
    name="changestation",
    description="Changes the radio station"
)

@app_commands.checks.cooldown(1, 5)
@app_commands.describe(stationid="The ID of the radio station to play")
@app_commands.autocomplete(stationid=radio_autocomplete)
@caliente.event
async def changestation(interaction: discord.Interaction, stationid: str):
    if interaction.guild.voice_client is None:
        await interaction.response.send_message("I am not connected to a voice channel.")
        return
    mycursor.execute('SELECT radio_url FROM radios WHERE radio_id = %s', (stationid,))
    station_url = mycursor.fetchone()
    if station_url is None:
        await interaction.response.send_message("Station ID not found.")
        return
    interaction.guild.voice_client.stop()
    interaction.guild.voice_client.play(discord.FFmpegPCMAudio(station_url[0], executable="ffmpeg"))
    await interaction.response.send_message(f"Changed station to {stationid}")

@tree.command(
    name="requeststation",
    description="Sends a request to add a station to the bot directory"
)

@app_commands.describe(station_url="Please note these are manually checked")

@caliente.event

async def addstation(interaction: discord.Interaction, station_name: str, station_url: str, station_id: str):
    class AddStationView(discord.ui.View):
        def __init__(self):
            super().__init__()
            
        @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
        async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
            mycursor.execute("INSERT INTO radios (radio_id, radio_name, radio_url) VALUES (%s, %s, %s)", (station_id, station_name, station_url))
            await interaction.response.send_message(f"Added station {station_name} with ID {station_id}")
        @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
        async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Station request denied.")
    mycursor.execute("SELECT * FROM radios WHERE radio_id = %s", (station_id,))
    result = mycursor.fetchall()
    if result:
        await interaction.response.send_message("Station ID already exists.")
        return
    
    embed_var = discord.Embed(title="New Station Request", color=discord.Color.green())
    embed_var.add_field(name="Station Name", value=station_name, inline=False)
    embed_var.add_field(name="Station URL", value=station_url, inline=False)
    embed_var.add_field(name="Station ID", value=station_id, inline=False)
    channel_thing = caliente.get_channel(1247386578859589633)
    await interaction.response.send_message("Station request sent.")

    await channel_thing.send(view=AddStationView(), embed=embed_var)
"""Helldiver Commands"""

helldiver_group = app_commands.Group(name="helldivers", description="Helldiver commands")
@helldiver_group.command(
    name="getplanetstats",
    description="Returns the planet statistics from the helldivers 2 api"
)

@caliente.event
async def get_planet(interaction: discord.Interaction, planetname: str):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "getplanetstats", 1, 5):
        await interaction.response.send_message("Preventing spamming so I dont get rate limited", ephemeral=True)
        return
    getting_planet = requests.get("https://api.helldivers2.dev/api/v1/planets")
    planets = getting_planet.json()
    found = False
    if planetname is None:
        await interaction.response.send_message("Please provide a planet name.")
        return
    for planet in planets:
        if planet["name"].lower() == planetname.lower():
            await interaction.response.send_message(f"Found planet! Getting planet info...")
            getting_planet_status = requests.get(f"https://api.helldivers2.dev/api/v1/planets/{planet['index']}")  
            if getting_planet_status.status_code != 200:
                await interaction.response.send_message("An error occurred while trying to get the planet status.")
                return
            planet_status = getting_planet_status.json()
            getting_hazards = [hazard['name'] for hazard in planet_status['hazards']]
            embed_var = discord.Embed(title=f"Planet {planet['name']} Statistics", color=discord.Color.blue())
            embed_var.add_field(name="Planet Sector", value=planet_status['sector'], inline=False)
            embed_var.add_field(name="Biome", value=planet_status['biome']['name'], inline=False)
            embed_var.add_field(name="Hazards", value=", ".join(getting_hazards), inline=False)
            embed_var.add_field(name="Health", value=planet_status['health'], inline=False)
            embed_var.add_field(name="Owned By", value=planet_status['currentOwner'], inline=False)
            embed_var.add_field(name="Active Helldivers", value=planet_status['statistics']['playerCount'], inline=False)
            break
    await interaction.followup.send(embed=embed_var)
    if not found:
        await interaction.response.send_message("Not found")
@helldiver_group.command(
    name="getevents",
    description="Returns current events from helldivers 2"
)

@caliente.event

async def getevents(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "getevents", 1, 30):
        await interaction.response.send_message("Helldiver event change once every 2 or something days calm down", ephemeral=True)
        return
    getting_events = requests.get("https://api.helldivers2.dev/api/v1/assignments")
    events = getting_events.json()
    event_embed = discord.Embed(title="Current events", color=discord.Color.red())
    if events == [""]:
        await interaction.response.send_message("No events found")
        return
    for event in events:
        event_embed.add_field(name=event['title'], value=event['briefing'], inline=False)
    await interaction.response.send_message(embed=event_embed)

@helldiver_group.command(
    name="galaxystats",
    description="Returns the galaxy statistics from helldivers 2"
)

@caliente.event

async def galaxystats(interaction: discord.Interaction):
    user_id = interaction.user.id
    if not check_rate_limit(user_id, "galaxystats", 5, 30):
        await interaction.response.send_message("I dont see why you need to spam this command? The thingy gets updated like, every 5 minutes or 15 minutes. Wait 30 seconds and try again", ephemeral=True)
        return
    await interaction.response.defer(thinking=True, ephemeral=False)
    getting_galaxy = requests.get("https://api-hellhub-collective.koyeb.app/api/statistics/galaxy")
    if getting_galaxy.status_code != 200:
        await interaction.followup.send("An error occurred while trying to get the galaxy statistics.") 
        return
    galaxy = getting_galaxy.json()
    galaxy_embed = discord.Embed(title="Galaxy statistics", color=discord.Color.green())
    galaxy_embed.add_field(name="Missions Won", value=galaxy['data']['missionsWon'], inline=False)
    galaxy_embed.add_field(name="Missions Lost", value=galaxy['data']['missionsLost'], inline=False)
    galaxy_embed.add_field(name="Terminids Killed", value=galaxy['data']['bugKills'], inline=False)
    galaxy_embed.add_field(name="Automatons Killed", value=galaxy['data']['automatonKills'], inline=False)
    galaxy_embed.add_field(name="Illuminates Killed", value=galaxy['data']['illuminateKills'], inline=False)
    galaxy_embed.add_field(name="Deaths", value=galaxy['data']['deaths'], inline=False)
    galaxy_embed.add_field(name="Friendly Kills", value=galaxy["data"]['friendlyKills'], inline=False)
    await interaction.followup.send(embed=galaxy_embed)

tree.add_command(helldiver_group)
"""AI Commands"""
ai_group = app_commands.Group(name="ai", description="AI commands")



@tree.command(
    name="sd3",
    description="Image generation from stable diffusion 3",
    guild=discord.Object()
)
@caliente.event
async def sd3(interaction: discord.Interaction, prompt: str, width: int=1024, height: int=1024, count: int=1, guidence: float=7.5, noise_fraction: float=0.8, prompt_strength: float=0.8, steps: int=50):
    await interaction.response.defer(thinking=True)
    if count < 1 or count > 4:
        await interaction.response.send_message("Count must be between 1 and 4")
        return
    if width > 1024 or height > 1024:
        await interaction.response.send_message("Width and height must be between 1024 and 1344")
        return
    if steps < 1 or steps > 100:
        await interaction.response.send_message("Steps must be between 1 and 100")
        return
    if guidence < 0 or guidence > 10:
        await interaction.response.send_message("Guidence scale must be between 0 and 10")
        return
    if noise_fraction < 0 or noise_fraction > 1:
        await interaction.response.send_message("High noise fraction must be between 0 and 1")
        return
    if prompt_strength < 0 or prompt_strength > 1:
        await interaction.response.send_message("Prompt strength must be between 0 and 1")
        return
    stable3 = llms.ImageGenerator()
    class ImageButtons(discord.ui.View):
        def __init__(self, *, timeout: float | None = 180):
            super().__init__(timeout=timeout)
        @discord.ui.button(label="Retry", style=discord.ButtonStyle.primary)
        async def retry(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.edit_original_response(content="Retrying...")
            image = create_image()
            await interaction.edit_original_response(content=f"Prompt: {prompt}", file=image, view=ImageButtons())
    def create_image(prompt=prompt, width=width, height=height, count=count, guidence=guidence, noise_fraction=noise_fraction, prompt_strength=prompt_strength, steps=steps):
        image = stable3.gen_image(prompt=prompt, count=count, width=width, height=height, guidance_scale=guidence, high_noise_frac=noise_fraction, prompt_strength=prompt_strength, num_inference_steps=steps)
        getting_image = requests.get(image['images'])
        with open("out-0.png", "wb") as f:
            f.write(getting_image.content)

        file = discord.File("out-0.png")
        prompt = prompt
        return file
    await interaction.followup.send(f"Prompt: {prompt}", file=create_image(), view=ImageButtons())


        

    # random_number = random.randint(1, 5)
    # session_hash = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

    # random_seed = random.randint(0, 2147483647)
    # await interaction.response.defer(thinking=True, ephemeral=False)
    # header = {
    #     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0",
    #     "Accept": "text/event-stream",  # Modified to accept SSE
    #     "Accept-Language": "en-US,en;q=0.5",
    #     "Content-Type": "application/json",
    #     "Origin": "https://stabilityai-stable-diffusion-3-medium.hf.space",
    #     "Referer": "https://stabilityai-stable-diffusion-3-medium.hf.space/?__theme=light"
    # }

    # url = "https://stabilityai-stable-diffusion-3-medium.hf.space/queue/join?__theme=light"
    # json_with_seed = {
    #     "data": [
    #         prompt,
    #         negative_prompts,
    #         seed,
    #         False,
    #         width,
    #         height,
    #         guidence_scale,
    #         steps
    #     ],
    #     "event_data": None,
    #     "fn_index": 1,
    #     "trigger_id": 5,
    #     "session_hash": session_hash
    #                     #v6lwy1nnk4s
    #                     #xiryxf6xcn
    # }

    # json_without_seed = {
    #     "data": [
    #         prompt, 
    #         negative_prompts,
    #         random_seed,
    #         True, # Random seed bool
    #         width,
    #         height,
    #         guidence_scale,
    #         steps
    #     ],
    #     "event_data": None,
    #     "fn_index": 1,
    #     "trigger_id": 5,
    #     "session_hash": "v6lwy1nnk4s"
    #                     #v6lwy1nnk4s
    #                     #xiryxf6xcn
    #                     #syp2i0rguh
    # }

    # if seed == 0:
    #     post = requests.post(url, headers=header, json=json_without_seed)
    # else:
    #     post = requests.post(url, headers=header, json=json_with_seed)

    # # Assuming your post request works correctly, setup the streaming GET request.
    # stream_url = f"https://stabilityai-stable-diffusion-3-medium.hf.space/queue/data?session_hash={session_hash}"
    # response = requests.get(stream_url, headers=header, stream=True)
    # print(f"Using session hash: {session_hash}")


    # # Process the SSE stream
    # try:
    #     for line in response.iter_lines():
    #         if line.startswith(b'data:'):
    #             # Remove "data: " prefix and decode bytes to string
    #             data = line.decode()[6:]
    #             try:
    #                 event_data = json.loads(data)
    #                 # Check if this is the completion event with the URL
    #                 if event_data.get("msg") == "process_completed":
    #                     # Extract URL from the nested structure
    #                     getting_image = requests.get(event_data["output"]["data"][0]["url"])
    #                     with open("output.png", "wb") as f:
    #                         f.write(getting_image.content)
    #                     file = discord.File("output.png")
    #                     await interaction.followup.send(f"Prompt: {prompt}, seed: {seed}", file=file)
    #                     os.remove("output.png")
    #                     break  # Exit after processing the complete event
    #             except json.JSONDecodeError:
    #                 print("Error decoding JSON")
    # except KeyboardInterrupt:
    #     # Handle manual interruption
    #     print("Stream stopped")
    # except Exception as e:
    #     # General error handling
    #     print("Error:", e)
    # finally:
    #     response.close() 

@ai_group.command(
    name="gemini",
    description="AI output from google gemini"
)

@caliente.event
async def gemini(interaction: discord.Interaction, message: str, attachment: discord.Attachment = None, instructions: str = None):
        user_id = interaction.user.id
        if not check_rate_limit(user_id, "gemini", 1, 5):
            await interaction.response.send_message("Please wait 5 seconds before doing this", ephemeral=True)
            return

        await interaction.response.defer(thinking=True, ephemeral=False)
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
        ]

        genai.configure(api_key=os.getenv("GENAI_API_KEY"))
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", system_instruction=instructions, safety_settings=safety_settings)
        #try:
        if attachment is None:
                response = model.generate_content([{"text": message}])
                if len(response.text) <= 2000:
                    await interaction.followup.send(response.text)
                elif len(response.text) > 2000:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".txt")
                    temp_file.write(response.text)
                    temp_file.seek(0)

                    discord_file = discord.File(temp_file.name, filename="output.txt")
                    await interaction.followup.send(file=discord_file)
        else:
            #try:
                await attachment.save(attachment.filename)
                uploaded_file = genai.upload_file(path=attachment.filename, display_name=attachment.filename)
                file = discord.File(attachment.filename, filename=attachment.filename)

                prompt_parts = [{"text": message}, uploaded_file]
                response = model.generate_content(prompt_parts)
                # file = discord.File(attachment, filename=attachment.filename)
                if len(response.text) <= 2000:
                    await interaction.followup.send(response.text, file=file)
                else:
                    temp_file = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".txt")
                    temp_file.write(response.text)
                    temp_file.seek(0)

                    discord_file = discord.File(temp_file.name, filename="output.txt")
                    await interaction.followup.send(files=[uploaded_file, discord_file])

                genai.delete_file(name=uploaded_file.name)
            #except Exception as e:
                #await interaction.followup.send(f"Failed to process image: {str(e)}")
    #except ValueError:
        #await interaction.followup.send("Your prompt was blocked")
tree.add_command(ai_group)
"""Developer Only Commands"""
@tree.command(
    name="setstatus",
    description="Pffff idk ",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def setstatus(interaction: discord.Interaction, activity: Literal["playing", "watching", "streaming", "listening"], status: str, url: str="https://lightningweb.xyz"):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    if activity == "playing":
        await caliente.change_presence(activity=discord.Game(name=status))
    elif activity == "watching":
        await caliente.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=status))
    elif activity == "streaming":
        await caliente.change_presence(activity=discord.Streaming(name=status, url=url))
    elif activity == "listening":
        await caliente.change_presence(activity=discord.Activity(type=discord.ActivityType.listening, name=status))
    await interaction.response.send_message("Status updated.")
@tree.command(
    name="clearcommands",
    description="Clears the commands from the bot",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def clear_global_commands(interaction: discord.Interaction):
    tree.clear_commands(guild=None)  # Clear globally
    await tree.sync()  # Sync globally
    await interaction.response.send_message("All global commands have been cleared.")
@tree.command(
    name="sync",
    description="SHUT THE FUCK UP!!!",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def sync_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    for guild in caliente.guilds:
        try:
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"Synced {len(tree.get_commands())} commands for {guild.name}")
            await asyncio.sleep(3)
        except discord.HTTPException:
            pass
    await interaction.followup.send("Synced commands")


@tree.command(
        name="update",
        description="Updates the bot",
        guild=discord.Object(662945359244558336)
)
async def update(interaction: discord.Interaction, update: str):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    with open("current_update.txt", "w") as f:
        f.write(update)
    await interaction.response.send_message("Updated the bot.")
    get_guild_channel_ids = "SELECT guild_id, channel_id FROM guilds_with_bot_updates"
    mycursor.execute(get_guild_channel_ids)
    guild_channel_ids = mycursor.fetchall()
    for guild_id, channel_id in guild_channel_ids:
        channel = caliente.get_channel(channel_id)
        if channel is not None:
            update_setting = "SELECT bot_updates FROM guilds_with_bot_updates WHERE guild_id = %s"
            if mycursor.execute(update_setting, (guild_id, )) == "True":
                print(f"Sending update to {guild_id}")
                await channel.send(f"New Update: {update}")
                asyncio.sleep(0.5)
@tree.command(
    name="testingcommand",
    description="Testing command",
    guild=discord.Object(662945359244558336)
)

@caliente.event
async def testingcommand(interaction: discord.Interaction):
    class ModalTest(discord.ui.Modal, title="Test"):
        name = discord.ui.TextInput(label='Name')
        answer = discord.ui.TextInput(label='Answer', style=discord.TextStyle.paragraph)

        async def on_submit(self, interaction: discord.Interaction):
            await interaction.response.send_message(f'Thanks for your response, {self.name}!', ephemeral=True)
    await interaction.response.send_modal(ModalTest())
@tree.command(
    name="requesttojoin",
    description="Request to join the guild",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def requesttojoin(interaction: discord.Interaction, guild_id: str, reason: str):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    guild = caliente.get_guild(int(guild_id))
    if guild is None:
        await interaction.response.send_message("Guild not found.")
        return
    guild_owner = guild.owner_id
    guild_name = guild.name
    developer_id = 489061310022156302
    developer = caliente.get_user(developer_id)
    await interaction.response.send_message(f"Request sent to {guild_name} owner.")
    class Buttonlol(discord.ui.View):
        def __init__(self, timeout=180):
            super().__init__(timeout=timeout)
        @discord.ui.button(label="Accept", style=discord.ButtonStyle.success)
        async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Request accepted.")
            await interaction.followup.send("Creating invite link...")
            invite = await guild.text_channels[0].create_invite(max_uses=1, max_age=43200)
            await interaction.followup.send(f"Invite link created")
            await developer.send(f"Invite link created for {guild_name}: {invite.url}")
        @discord.ui.button(label="Deny", style=discord.ButtonStyle.danger)
        async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
            await interaction.response.send_message("Request denied.")
            await developer.send(f"Request denied for {guild_name}")
    await caliente.get_user(guild_owner).send(f"Bot developers have requested to join your server for this reason: {reason}. If you accept this, then the bot will create an invite link that will last only for 12 hours with one use. Do you accept?", view=Buttonlol())
@tree.command(
    name="getguilds",
    description="Gets the guilds the bot is in",
    guild=discord.Object(662945359244558336)
)

@caliente.event 

async def getguilds(interaction: discord.Interaction):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    guilds = caliente.guilds
    guild_list = []
    for guild in guilds:
        guild_list.append(f"{guild.name} (ID: {guild.id})")
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".txt") as temp_file:
        temp_file.write('\n'.join(guild_list))
        temp_file_path = temp_file.name
    
    await interaction.response.send_message(
        content=f"Bot is in {len(guilds)} guilds:",
        file=discord.File(temp_file_path)
    )
@tree.command(
    name="eval",
    description="Evaluates code",
    guild=discord.Object(662945359244558336)
)

@caliente.event


async def eval(interaction: discord.Interaction):
    local_vars = {
        "caliente": caliente,
        "interaction": interaction,
        "discord": discord,
        "app_commands": app_commands,
        "commands": commands,
        "bot": caliente,
        "mysql": mysql,
        "mycursor": mycursor,
        "redis_timeout_client": redis_timeout_client,
        "uuid": uuid
    }
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    # try:

    #     await interaction.response.defer(thinking=True)
    #     buffer = io.StringIO()
    #     with contextlib.redirect_stdout(buffer):
    #         exec(f"async def func():\n  {code}", local_vars)
    #         await local_vars["func"]()
    #     result = buffer.getvalue()
    #     await interaction.followup.send(f"Result: {result}")
    # except Exception as e:
    #     await interaction.followup.send(f"Error: {e}")
    class EvalModal(discord.ui.Modal, title="Code Evaluation"):
        code = discord.ui.TextInput(label="Code", placeholder="Enter code here", style=discord.TextStyle.paragraph)
        async def on_submit(self, interaction: discord.Interaction):
            code = self.code.value
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                exec(f"async def func():\n  {code}", local_vars)
                await local_vars["func"]()
            result = buffer.getvalue()
            await interaction.response.send_message(f"Result: {result}")
    view = EvalModal()
    await interaction.response.send_modal(view)


@tree.command(
    name="error",
    description="Causes an intentioned Exception error. Used for testing purposes",
)

@caliente.event
async def error(interaction: discord.Interaction, message: str):
    raise Exception(message)

@tree.command(
    name="sql",
    description="Runs an sql query on either mysql or PostgreSQL",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def sqlthingy(interaction: discord.Interaction, service: Literal["mysql", "postgreSQL"], query: str):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    if service == "mysql":
        mycursor.execute(query)
        result = mycursor.fetchall()
        await interaction.response.send_message(f"Result: {result}")
    elif service == "postgreSQL":
        postcurse.execute(query)
        if query.startswith("SELECT"):
            result = postcurse.fetchall()
            await interaction.response.send_message(f"Result: {result}")
        else:
            await interaction.response.send_message("Executed query.")
    else:
        await interaction.response.send_message("Invalid service.")
# @tree.command(
#     name="addshopitem",
#     description="Adds an item to the shop",
#     guild=discord.Object(662945359244558336)
# )

# @caliente.event

# async def addshopitem(interaction: discord.Interaction, rarity: Literal["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"], item: str, price: int, quantity: int = 50):
#     if interaction.user.id != 489061310022156302:
#         await interaction.response.send_message("You don't have permission to use this command.")
#         return
#     try:
#         add_item = sql.SQL("INSERT INTO shop_items (item_name, item_rarity, item_cost, item_quantity) VALUES (%s, %s, %s, %s)")
#         postcurse.execute(add_item, (item, rarity, price, quantity))
#         connector.commit()
#         await interaction.response.send_message("Item added to the shop.")
#     except Exception as e:
#         print(f"An error occurred: {e}")
@tree.command(
    name="blacklist",
    description="HAHAHA I BLACKLISTED THIS FUCKING GUILD",
    guild=discord.Object(662945359244558336)
)

@caliente.event

async def blacklist(interaction: discord.Interaction, guild_id: str, reason: str = "No reason provided"):
    if interaction.user.id != 489061310022156302:
        await interaction.response.send_message("You don't have permission to use this command.")
        return
    mycursor.execute("SELECT guild_id, guild_name FROM guilds WHERE guild_id = %s", (guild_id,))
    result = mycursor.fetchone()
    guild_name = result[1]
    guild = caliente.get_guild(int(guild_id))
    owner_id = guild.owner_id
    if guild_id not in result:
        await interaction.response.send_message("Guild not found")
    else:
        await interaction.response.send_message("This guild is already blacklisted")
    
    
    sql = "INSERT INTO blacklisted (guild_id, guild_name, reason, owner_id) VALUES (%s, %s, %s, %s)"
    val = (str(guild_id), guild_name, reason, str(owner_id))
    mycursor.execute(sql, val)
    guild_db.commit()
    
    await guild.leave()
    await interaction.response.send_message("Blacklisted Guild")

    caliente.dispatch("blacklist", guild_id)

# create = app_commands.Group(name="create", description="Group for creating items or anything idk", guild_only=True, guild_ids=[662945359244558336])

# @create.command(
#     name="job",
#     description="Creates a job and adds it to jobs.json",
# )
# @app_commands.autocomplete(item_requirements=item_autocomplete)
# @caliente.event

# async def createjob(interaction: discord.Interaction, job_category: Literal["Regular Jobs", "Premium Jobs"], job_name: str, job_description: str, job_pay: int, job_id: int, job_icon: discord.Attachment = None, item_requirements: str = None):
#     if interaction.user.id != 489061310022156302:
#         await interaction.response.send_message("You don't have permission to use this command.")
#         return
#     with open("Gamble/items.json", "r") as f:
#         items = json.load(f)
    
#     json_stuff = {
#         "job_name": job_name.lower(),
#         "details": {
#             "displayname": job_name,
#             "description": job_description,
#             "payperday": job_pay,
#             "icon": job_icon.url if job_icon else None,
#             "job_id": job_id
#         }
#     }
#     jobname = job_name.capitalize()
#     code_to_create = f"""
#     class {jobname}(ui.Modal, title=title): 
#         name=ui.TextInput(label="Name", placeholder="Your name")
#         experience=ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph)
#         description=ui.TextInput(label="Description", placeholder="Anything Else?", style=discord.TextStyle.paragraph)
        
#         async def on_submit(self, interaction: discord.Interaction):
#             await interaction.response.send_message("Job application submitted, this will take one minute to process...")
#     """
#     with open("important_stuff/modals.py", "a") as f:
#         f.write(code_to_create)
        

#     if item_requirements:
#         item_id = None
#         for category in items:
#             if item_requirements in items[category]:
#                 item_id = items[category][item_requirements]["item_id"]
#                 break

#         if item_id is None:
#             await interaction.response.send_message("Item not found.")
#             return

#         json_stuff["details"]["required_items"] = {"item_id": item_id}

#     with open("Gamble/jobs.json", "r") as f:
#         jobs = json.load(f)
#     jobs[job_category].append(json_stuff)
#     with open("Gamble/jobs.json", "w") as f:
#         json.dump(jobs, f, indent=4)
#     await interaction.response.send_message("Job created.")
# @create.command(
#     name="item",
#     description="Creates an item and adds it to items.json",
# )

# @caliente.event

# async def createitem(interaction: discord.Interaction, item_name: str, item_description: str, item_id: int, value: int, item_rarity: Literal["Common", "Uncommon", "Rare", "Epic", "Legendary", "Mythical"], icon: discord.Attachment = None):
#     item_json = {
#         item_name: {
#             "value": value,
#             "icon": icon.url if icon else None,
#             "item_id": item_id,
#             "description": item_description
#         }
#     }

#     with open("Gamble/items.json", "r") as f:
#         items = json.load(f)
#         items[item_rarity].update(item_json)
#     with open("Gamble/items.json", "w") as f:
#         json.dump(items, f, indent=4)
#     await interaction.response.send_message("Item created.")

# tree.add_command(create)

@tree.command(
    name="jsondbtesting",
    description="Testing json db",
    guild=discord.Object(662945359244558336)
)

@caliente.event
async def jsontesting(interaction: discord.Interaction, key: str, value: str):
    json_stuff = {
        key: value,
    }

    json_str = json.dumps(json_stuff)
    postcurse.execute("INSERT INTO json_testing (testing) VALUES (%s)", (json_str,))
    
    await interaction.response.send_message("Inserted into json_testing")



# @tree.command(
#     name="testingpagemodals",
#     description="Yeah"
# )
# @caliente.event

# async def testinglmao(interaction: discord.Interaction):
#     await interaction.response.send_modal(accounting.AccountingMath())

#     text_inputs = [
#         ui.TextInput(label="Name", placeholder="Your name", style=discord.TextStyle.short),
#         ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph),
#         ui.TextInput(label="Have you had some past e", placeholder="Past experience", style=discord.TextStyle.long),
#         ui.TextInput(label="Have you worked on any p", placeholder="Past contracts", style=discord.TextStyle.long),
#         ui.TextInput(label="What military vehicle works best?", placeholder="Military vehicles", style=discord.TextStyle.long),
#         ui.TextInput(label="Are you retired or active military?", placeholder="Retired or active", style=discord.TextStyle.short),
#         ui.TextInput(label="If so, which branch?", placeholder="branch", style=discord.TextStyle.short),
#         ui.TextInput(label="Should we know anything else?", placeholder="Anything else?", style=discord.TextStyle.paragraph),
#     ]

#     BUTTONS = {
#     # remove cancel button
#     "CANCEL": None,
#         # remove the next button
#     "NEXT": None,
#         # change open button's label to "Open Modal" (default is "Open")
#     "OPEN": CustomButton(label="Open Modal"),
#     }

#     paginatior = job_modals.ModalPagesTest.from_text_inputs(
#         *text_inputs,
#         author_id=interaction.user.id,
#         default_title="Testing",
#         buttons=job_modals.ModalPagesTest.BUTTONS,
#         can_go_back=False
#     )

#     await paginatior.send(interaction)
# @tree.command(
#     name="botsupport",
#     description="Have an issue? You can chat with the bot developer or administrator to help fix your problem",
# )

# @caliente.event

# async def farmtesting(interaction: discord.Interaction, issue: str):
#     if "logging" in issue:
#         text = "To setup logging, you can do /setloggingchannel. Please keep in mind that this records all bans, kicks and mutes that are only executed by the bot. We will address this issue in the near future."
#     if "mute" in issue:
#         text = "You can use /setmuterole to set the mute role. This will allow our bot to mute users whenever you execute /mute or /unmute. Keep in mind there is no time limit for the mute role, you will have to manually unmute the user."
#     if "balance" or "money" or "cash" in issue:
#         text = "If you are wondering why you don't have a balance, you must do /eco start. This will give you a prompt saying that if you are ready. Click the 'Start' button to register your self in the economy database."
#     await interaction.user.send(f"Thank you for reaching out! Please keep in mind that you may not receive an immediate response or your response might be automatically deleted. Your issue is: {issue}")
#     await asyncio.sleep(2)
#     await interaction.user.send(f"While you wait, here is a suggestion to help with your issue: \n{text}")
#     await asyncio.sleep(2)
#     await interaction.user.send("Also join our [discord](https://discord.gg/u2YBbHjJRh)")
#     channel = caliente.get_channel(1244914941732061234)
#     thread = await channel.create_thread(name=f"{interaction.user.id}")
#     await channel.send(f"User {interaction.user} has an issue: {issue}, thread: {thread.mention}")
#     dm_channel = await interaction.user.create_dm()

#     messages = dm_channel.history(limit=5)

#     for message in messages:
#         await thread.send(f"{message.author}: {message.content}")

    
caliente.run(token=token)

# I have a discord bot called Bot-Bot, it is a multipurpose bot that has a global economy system, reputation system and many customizable options. At the top of the main page, I want a login button. Now I want 2 pages: 
# A dashboard place holder, this will act as a list of guilds for the user which are clickable
# A guild place holder, on this page there will be 1 dropdown menu for channels and buttons that are named "Change Suggestions Channel", "Change Reputation Channel", and "Change logging channel". Another drop down menu which will be a place holder for the roles and a button that says "Set mute role". 