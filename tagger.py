"""
Simple logging script for OBS. The purpose of this script is to log when a game starts and ends
in stream, to make it easier to find correct timestamps for cutting individual VODs from the
recording later. Game ID is retrieved from an API endpoint that has a 'current_game' attribute
available.

The script can be configured via three properties:
- List of scene names, transitioning into these scenes is considered game starting
- Log file path, where to write the log
- API endpoint, where to look for current game's ID.
"""

import datetime
import requests
import obspython as obs

data = {
    "settings": None,
    "in_game_scene": False,
    "current_game": None
}


# Functions OBS calls on load
# v

def script_load(settings):
    """
    Called when OBS loads the script. Stores the settings data object to be used later, and
    adds our only callback.
    """

    obs.obs_frontend_add_event_callback(handle_event)
    data["settings"] = settings

def script_properties():
    """
    Also called when the script is loaded, defines the properties of the script that can be
    configured from the script window UI. OBS connects these automatically to values in the
    settings object in the background.
    """

    props = obs.obs_properties_create()
    scene_field = obs.obs_properties_add_editable_list(
        props, "gamescene", "Game scene names",
        obs.OBS_EDITABLE_LIST_TYPE_STRINGS, "", "."
    )
    logfile_field = obs.obs_properties_add_text(
        props, "logfile", "Log file path", obs.OBS_TEXT_DEFAULT
    )
    api_field = obs.obs_properties_add_text(
        props, "apiurl", "API endpoint", obs.OBS_TEXT_DEFAULT
    )
    return props

def script_description():
    """
    Called when the script is loaded, shows its description.
    """

    return "Logs timestamp and game ID from API when switching to and from specified scene."


# Tool functions
# v

def log_transition(end=False):
    """
    Logs the transition into a file. The optional parameter 'end' determines whether the
    transition is tagged as game starting or ending.
    """

    timestamp = datetime.datetime.now().isoformat()
    event = ["START", "END"][end]
    with open(obs.obs_data_get_string(data["settings"], "logfile"), "a") as logfile:
        logfile.write(
            f"[{timestamp}] {event} {data["current_game"]}\n"
        )

def set_game():
    """
    Sets current game into the internal data dictionary by retrieving it from the API.
    """

    resp = requests.get(obs.obs_data_get_string(data["settings"], "apiurl"))
    if resp.status_code == 200:
        data["current_game"] = resp.json()["current_game_id"]
    else:
        print("Failed to get data from API")


# Event handlers
# v

def handle_event(event):
    """
    Handles events. Our handler is only interested in scene change. Setting values are always
    re-read when this function is called to make sure any changes are always applied.

    Game is considered as starting if we are going into any of the game scenes, and similarly
    ended when going into any of the non-game scenes.
    """

    if event == obs.OBS_FRONTEND_EVENT_SCENE_CHANGED:
        scene = obs.obs_frontend_get_current_scene()
        scene_name = obs.obs_source_get_name(scene)

        # OBS arrays are very fun!
        game_scene_array = obs.obs_data_get_array(data["settings"], "gamescene")
        game_scenes = []
        for i in range(obs.obs_data_array_count(game_scene_array)):
            scene_item = obs.obs_data_array_item(game_scene_array, i)
            game_scenes.append(obs.obs_data_get_string(scene_item, "value"))
            obs.obs_data_release(scene_item)
        obs.obs_data_array_release(game_scene_array)

        if not data["in_game_scene"] and scene_name in game_scenes:
            print("Entering game")
            set_game()
            log_transition()
            data["in_game_scene"] = True
        elif data["in_game_scene"] and scene_name not in game_scenes:
            print("Leaving game")
            log_transition(end=True)
            data["in_game_scene"] = False

