import discord
from discord import app_commands
from discord.ext import commands
from important_stuff.permission import moderator_permissions, admin_permissions
import psycopg2

connector = psycopg2.connect(
    dbname="",
    user="",
    password="",
    host="",
    port=""
)

postcurse = connector.cursor() 
postcurse.connection.autocommit = True


def has_permissions():
    async def predicate(interaction: discord.Interaction):
        admin_check = admin_permissions(interaction.user)
        moderator_check = moderator_permissions(interaction.user)
        owner_check = interaction.user.id == interaction.guild.owner_id
        
        # Debugging outputs to trace the decision process
        print(f"Admin Check: {admin_check}")
        print(f"Moderator Check: {moderator_check}")
        print(f"Owner Check: {owner_check}")
        
        if admin_check or owner_check or moderator_check:
            return True
        else:
            await interaction.response.send_message("You do not have permissions to use this command", ephemeral=True)
            return False
    return app_commands.check(predicate)