import os
import nextcord
from nextcord.ext import commands
from nextcord import SlashOption


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot



    @nextcord.slash_command(name="sync", description="Sync all commands", guild_ids=[987693509215658035])
    async def sync(self, i: nextcord.Interaction):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        await i.response.defer()
        try:
            await self.bot.sync_all_application_commands()
            await i.edit_original_message(content="Synced all slash commands")
        except Exception as e:
            await i.edit_original_message(content=f"Something weird happened while syncing: {e}")



    @nextcord.slash_command(name="reloadall", description="Reload all cogs", guild_ids=[987693509215658035])
    async def reload_all_cogs(self, i: nextcord.Interaction):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        try:
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    self.bot.reload_extension(f'cogs.{filename[:-3]}')
                    print(f"Reloaded {filename}")
            await i.send(f"Reloaded {len(self.bot.cogs)} cogs", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"Failed to reload all cogs: {e}", ephemeral=False)



    @nextcord.slash_command(name="loadall", description="Load all cogs", guild_ids=[987693509215658035])
    async def load_all_cogs(self, i: nextcord.Interaction):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        try:
            for filename in os.listdir('./cogs'):
                if filename.endswith('.py'):
                    self.bot.load_extension(f'cogs.{filename[:-3]}')
                    print(f"Loaded {filename}")
            await i.send(f"Loaded {len(self.bot.cogs)} cogs", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"Failed to load all cogs: {e}", ephemeral=False)



    @nextcord.slash_command(name="reload", description="Reload a cog", guild_ids=[987693509215658035])
    async def reload_cog(self, i: nextcord.Interaction, cog: str = SlashOption(description="Cog to reload", required=True, choices=sorted([cog[:-3] for cog in os.listdir('./cogs') if cog.endswith('.py')]))):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        try:
            self.bot.reload_extension(f'cogs.{cog}')
            await i.response.send_message(f"Reloaded cog `{cog}`", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"Failed to reload cog `{cog}`: {e}", ephemeral=False)



    @nextcord.slash_command(name="unload", description="Unload a cog", guild_ids=[987693509215658035])
    async def unload_cog(self, i: nextcord.Interaction, cog: str = SlashOption(description="Cog to unload", required=True, choices=[cog[:-3] for cog in os.listdir('./cogs') if cog.endswith('.py')])):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        try:
            self.bot.unload_extension(f'cogs.{cog}')
            await i.response.send_message(f"Unloaded cog `{cog}`", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"Failed to unload cog `{cog}`: {e}", ephemeral=False)



    @nextcord.slash_command(name="load", description="Load a cog", guild_ids=[987693509215658035])
    async def load_cog(self, i: nextcord.Interaction, cog: str = SlashOption(description="Cog to load", required=True, choices=[cog[:-3] for cog in os.listdir('./cogs') if cog.endswith('.py')])):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        try:
            self.bot.load_extension(f'cogs.{cog}')
            await i.response.send_message(f"Loaded cog `{cog}`", ephemeral=True)
        except Exception as e:
            await i.response.send_message(f"Failed to load cog `{cog}`: {e}", ephemeral=False)



    @nextcord.slash_command(name="changestatus", description="Ändere den Custom Status des Bots")
    async def changestatus(self, i: nextcord.Interaction, status: str = SlashOption(description="Status des Bots", required=False), online_status: str = SlashOption(description="Online Status des Bots", choices=["online", "idle", "dnd", "invisible"], required=False)):
        if i.user.id not in (1107002211306852443, 399668151475765258):
            await i.send("Lass gut sein, du idiot.", ephemeral=True)
            return
        
        status_mapping = {
            "online": nextcord.Status.online,
            "idle": nextcord.Status.idle,
            "dnd": nextcord.Status.dnd,
            "invisible": nextcord.Status.invisible
        }
        online_status_converted = status_mapping.get(online_status, nextcord.Status.online)
        
        if status:
            custom = nextcord.CustomActivity(name=status)
            await self.bot.change_presence(activity=custom, status=online_status_converted)
            await i.response.send_message(f"Changed status to {status} and online status to {online_status}", ephemeral=True)
        else:
            await self.bot.change_presence(activity=None, status=online_status_converted)
            await i.response.send_message(f"Status reset and online status changed to {online_status}", ephemeral=True)



def setup(bot):
    bot.add_cog(Admin(bot))
