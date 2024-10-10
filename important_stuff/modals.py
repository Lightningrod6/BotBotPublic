from discord import ui
import discord
import redis
import asyncio
from random import randint
import logging
redis_application_client = redis.Redis(host="viaduct.proxy.rlwy.net", port=22380, db=0, username="default", password="rwraWPkonPdzAiyyOEuOWkOKrkZRGztl")

title="Bot-Bot Employment Office"
random_number = randint(30, 60)
class CoalMinerJob(ui.Modal, title=title):

    name=ui.TextInput(label="Name", placeholder="Your name")
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.delete_original_response()
        # redis_application_client.set(f"job_application:{interaction.user.id}", "Coal Miner")
        # redis_application_client.expire(f"job_application:{interaction.user.id}", 40)
        # remaining_time = redis_application_client.ttl(f"job_application:{interaction.user.id}")
        coal_mines = ["Black Thunder Mine", "Dunglas Coal Mine", "Creek Hill Mine", "Yoaksmite Mining Group", "Black Thunder Mine, Texas", "Will & Brothers Mining Group", "Old Ruckus Mining Industries", "MillSorow Mines, Kentucky", "Millsorow Mines, California"]
        location = coal_mines[randint(0, len(coal_mines)-1)]
        await interaction.response.send_message(f"The mining company at {location} recieved your application, please wait for a response. This will a minute")
        await asyncio.sleep(random_number)
        await interaction.user.send("Your job application has been accepted, you now have access to /job work. You can now start making money!")
class BlackSmithJob(ui.Modal, title=title):

    name=ui.TextInput(label="Name", placeholder="Your name")
    experience=ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph)
    stuffyouvemade=ui.TextInput(label="Stuff you have made", placeholder="What have you made?", style=discord.TextStyle.long)
    ableto=ui.TextInput(label="Able to handle hot stuff?", placeholder="Can you handle hot stuff? like lava, fire, etc...", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        blacksmithsubsidaries = ["Vailage Smithing East", "Vailage Smithing South", "Bot-Bot Smithing INC", "Weltale Welding", "Swords And Shields Enterprises", "Smiths Smithing", "United Blacksmiths", "Warshaw Smithing Subsidary", "Casters United, East", "Casters United, Regional"]
        location = blacksmithsubsidaries[randint(0, len(blacksmithsubsidaries)-1)]
        await interaction.edit_original_response(f"{location} were able to receive your application. This will take a minute to go over")
        await asyncio.sleep(random_number)
        await interaction.user.send("Your job application has been accepted, you now have access to /job work. You can now start making money!")
class DroneOperatorJob(ui.Modal, title=title):
    name=ui.TextInput(label="Name", placeholder="Your name")
    experience=ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph)
    dronesflown=ui.TextInput(label="Drones Flown", placeholder="Any drones flown in the past", style=discord.TextStyle.long)
    pastjobs=ui.TextInput(label="Past Jobs", placeholder="Any past jobs?", style=discord.TextStyle.paragraph)
    description=ui.TextInput(label="Description", placeholder="Anything Else?", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        dronecompanies = ["DroneX", "LoX Defense, Drone Division", "Flying Objects", "Skyward Global, Drone Defense", "Kingsman Drones", "X-Defense, Drone Sector", "Lightning Defense, Drone Division", "Raytheon, Western Drone Divison", "Raytheon, Eastern Drone Divison", "Civil Drone Operations"]
        location = dronecompanies[randint(0, len(dronecompanies)-1)]
        await interaction.edit_original_response(f"{location} has recieved your application, this will take a minute to process")
        await asyncio.sleep(random_number)
        await interaction.user.send(f"{location} would like to have you on their team, you now have access to /job work. You can now start making money!")

class PodCastHostJob(ui.Modal, title="TOPG Podcast Host"):
    onequestion=ui.TextInput(label="So do you have", placeholder="What it takes to be a TOPG")
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.delete_original_response()
        webhook = await interaction.channel.create_webhook(name="Andrew Tate")
        await webhook.send("Welcome to the TOPG crew bro, Make sure to record epsiodes daily. I am counting on you", avatar_url="https://images.moneycontrol.com/static-mcnews/2022/08/Andrew-tate-770x435.jpg")

class MilitaryEngineer(ui.Modal, title=title): 
    name=ui.TextInput(label="Name", placeholder="Your name")
    experience=ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph)
    projects=ui.TextInput(label="Past Projects", placeholder="Any past projects?", style=discord.TextStyle.long)
    vehiclgoodat=ui.TextInput(label="Military Vehicles you are good at", placeholder="Good with any military vehicles?", style=discord.TextStyle.paragraph)
    #anotherquestion=ui.TextInput(label="Retired or Current Military?", placeholder="Retired or active", style=discord.TextStyle.paragraph)
   # ifso=ui.TextInput(label="If so, which branch?", placeholder="branch", style=discord.TextStyle.paragraph)
    description=ui.TextInput(label="Description", placeholder="Anything Else?", style=discord.TextStyle.paragraph)
        
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.delete_original_response()
        facilities = ["Fort Sill", "LoX Defense", "Skyward Global, Military Division", "X-Defense", "Lightning Defense", "United Coalition, Military Middle East", "Hellfire Engineering", "Raytheon, Central Military Division", "GroundWorks Engineering, Civil Defense Sector", "General Electric, Engineering Division"]
        location = facilities[randint(0, len(facilities)-1)]    
        await interaction.response.send_message(f"Your application is being sent to {location}, it will be processed as soon as it gets there")
        await asyncio.sleep(random_number)
        await interaction.user.send("Your job application has been accepted, you now have access to /job work. You can now start making money!")

class AccountingJob(ui.Modal, title=title): 
    name=ui.TextInput(label="Name", placeholder="Your name")
    experience=ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph)
    goodwithnumbers=ui.TextInput(label="Are you good with numbers?", placeholder="Can you handle numbers well?", style=discord.TextStyle.short)
    description=ui.TextInput(label="Description", placeholder="Anything Else?", style=discord.TextStyle.paragraph)
    async def on_submit(self, interaction: discord.Interaction):
        accountingfirms = ["Yahoo Finance", "NYSE Accounting", "Monchrome Accounting Solutions", "MillSorow Mines, Accounting Sector", "Enterprise Solutions, New York", "Greenwich Services", "East Coast Money Solutions", "Dividend jones", "Bloomberg+", "Kella & Bob Solutions", "Will, S. Conward & Associates"]
        location = accountingfirms[randint(0, len(accountingfirms)-1)]
        await interaction.response.send_message(f"{location} has recieved your application, this will take a minute to process")
        await asyncio.sleep(random_number)
        await interaction.user.send("Your job application has been accepted, you now have access to /job work. You can now start making money!")


# class ModalPagesTest(ModalPaginator):
#     text_inputs = [
#         ui.TextInput(label="Name", placeholder="Your name", style=discord.TextStyle.short),
#         ui.TextInput(label="Experience", placeholder="Your experience", style=discord.TextStyle.paragraph),
#         ui.TextInput(label="Have you had some past experience?", placeholder="Past experience", style=discord.TextStyle.long),
#         ui.TextInput(label="Have you worked on any past contracts?", placeholder="Past contracts", style=discord.TextStyle.long),
#         ui.TextInput(label="What are some military vehicles that you work best with?", placeholder="Military vehicles", style=discord.TextStyle.long),
#         ui.TextInput(label="Are you retired or active military?", placeholder="Retired or active", style=discord.TextStyle.short),
#         ui.TextInput(label="If so, which branch?", placeholder="branch", style=discord.TextStyle.short),
#         ui.TextInput(label="Should we know anything else?", placeholder="Anything else?", style=discord.TextStyle.paragraph),
#     ]

#     MODAL_TITLE = title

#     @property
#     def page_string(self) -> None:
#         total_modals = len(self.modals)

#         current_modal_index = self.current_page + 1

#         return f"Please go through all the modals and submit them ({current_modal_index}/{total_modals})."

#     async def on_finish(self, interaction: discord.Interaction) -> None:
#         answers = [f"**{tinput.label}**: {tinput.value}" for tinput in self.text_inputs]

#         await interaction.response.send_message("\n".join(answers), ephemeral=True)