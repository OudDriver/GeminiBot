from commands.list import setup_list_command
from commands.uwuify import setup_uwu_command
from commands.toggle import setup_toggle_command
from commands.which import setup_which_command

def register_commands(client, initial_state, config):
    setup_uwu_command(client, initial_state)
    setup_toggle_command(client, initial_state, config)
    setup_which_command(client, initial_state, config)
    setup_list_command(client, initial_state)