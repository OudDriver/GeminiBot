from discord.ext import commands
from packages.utils import save_temp_config
import logging

def setup_uwu_command(client, initial_state):  
    @client.hybrid_command(name="uwuify")
    @commands.has_permissions(manage_messages=True)
    async def uwuify(ctx: commands.Context):
        """Why!?!?"""
        initial_state["current_uwu_status"] = not initial_state["current_uwu_status"]
        save_temp_config(initial_state["model"], initial_state["system_prompt_data"], initial_state["current_uwu_status"])

        if initial_state["current_uwu_status"]:
            await ctx.reply("Enabled Uwuifier. Beware that asking it for code will not work.")
            logging.info("Enabled Uwuifier.")
        else:
            await ctx.reply("Disabled Uwuifier.")
            logging.info("Disabled Uwuifier.")