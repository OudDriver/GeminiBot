import discord
from discord.ext import commands
from discord import app_commands
from bot.setup import save_temp_config
import logging

def setup_toggle_command(client, initial_state, config):  
    model_options = initial_state["model_options"]
    system_prompts = initial_state["system_prompts"]
    tools = initial_state["tools"]

    @client.hybrid_command(name="toggle")
    @app_commands.choices(toggles=[
        app_commands.Choice(name="System Prompt", value="sys"),
        app_commands.Choice(name="Model", value="model"),
        app_commands.Choice(name="Tools", value="tools")
    ])
    async def toggle(ctx: commands.Context, toggles: str):
        """Toggles something for the bot."""

        if toggles == 'sys':
            
            initial_state["current_model_index"] = (initial_state["current_model_index"] + 1) % len(model_options)
            initial_state["model"] = model_options[initial_state["current_model_index"]]

            initial_state["current_sys_prompt_index"] = (initial_state["current_sys_prompt_index"] + 1) % len(system_prompts)
            initial_state["system_prompt_data"] = system_prompts[initial_state["current_sys_prompt_index"]]['SystemPrompt']
            system_prompt_name = system_prompts[initial_state["current_sys_prompt_index"]]['Name']

            save_temp_config(initial_state["model"], initial_state["system_prompt_data"], initial_state["current_uwu_status"])
            logging.info(f"Switched to {system_prompt_name}")
            await ctx.send(f"Using {system_prompt_name}.")

        elif toggles == "model":
            
            initial_state["current_model_index"] = (initial_state["current_model_index"] + 1) % len(model_options)
            initial_state["model"] = model_options[initial_state["current_model_index"]]

            save_temp_config(initial_state["model"], initial_state["system_prompt_data"], initial_state["current_uwu_status"])
            friendly_name = config["ModelNames"][initial_state["model"]]
            logging.info(f"Switched to {friendly_name}")
            await ctx.send(f"Switched to {friendly_name}")
            await client.change_presence(activity=discord.CustomActivity(name=f'Hello there! I am using {friendly_name}'))

        elif toggles == 'tools':
            
            tools_names = list(tools.keys())
            initial_state["active_tools_index"] = (initial_state["active_tools_index"] + 1) % len(tools_names)
            initial_state["active_tools"] = tools[tools_names[initial_state["active_tools_index"]]]
            logging.info(f"Switched to toolset {tools_names[initial_state['active_tools_index']]}")
            await ctx.send(f"Switched to toolset: {tools_names[initial_state['active_tools_index']]}")
