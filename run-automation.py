#
# Personal automation based on Tasmota MQTT and Paho and Assitant relay.
#
import json
import sys
import time

import  httpx
import trio

from trio_tasmota import TasmotaAdapter

BRIDGE_NAME = "tasmota_zbBridge"
HOST = "172.19.0.31"
MQTT_ADDRESS = HOST
GOOGLE_URL = "http://{}:3000".format(HOST)

# Action to controllor cat litter vacuum.
LITTER_BUTTON = "0xF2F3"
# Ikea light sensonr
LIGHT_SENSOR = "0x961B"
# Light bulb from the stairs
LIGHT_STAIRS = "0x37CA"
# Ikea 2 buttons for office room.
SWITCH_1 = "0x999D"
# Ikea 2 buttons for down control room.
SWITCH_2 = "0xEB2D"

EVENT_IKEA_BUTTON_0_SHORT = "0006!00"
EVENT_IKEA_BUTTON_1_SHORT = "0006!01"

EVENT_IKEA_BUTTON_1_LONG_START = '0008!05'


def get_sensors():
    return {
        LITTER_BUTTON: on_ikea_action1,
        SWITCH_1: on_switch_1,
        SWITCH_2: on_switch_1,
    }


ikea_action1_down_start = 0
ikea_move1_last = 0


# Helper to detect long press.
ikea_long_start = 0, 0

async def on_switch_1(client, payload):
    """
    Called when switch 1 was pressed
    """
    global ikea_long_start
    if EVENT_IKEA_BUTTON_1_SHORT in payload:
        return await tasmota.zb_power(LIGHT_STAIRS, 2)

    if EVENT_IKEA_BUTTON_0_SHORT in payload:
        # Do nothing
        return

    if 'DimmerMove' in payload:
        # Start for long press.
        ikea_long_start = time.time(), payload['DimmerMove']
        return

    start_time, dimmer_move = ikea_long_start
    # Most probabling long press released.
    # Maximum value is like 5 seconds.
    duration = min(time.time() - start_time, 1)
    _log("Duration " + str(duration))

    direction = 1
    if dimmer_move == 1:
        direction = -0.8

    offset = duration * 128

    dim = 127 + direction * offset
    return await tasmota.zb_dim(LIGHT_STAIRS, dim)



async def on_ikea_action1(client, payload):
    """ """
    global ikea_action1_down_start

    if EVENT_IKEA_BUTTON_1_SHORT in payload:
        return await google_home("start vacuuming the hall")

    if EVENT_IKEA_BUTTON_1_LONG_START in payload:
        # Long press started.
        ikea_action1_down_start = time.time()
        return

    # Most probabling long press released.
    duration = time.time() - ikea_action1_down_start

    if duration > 1.5:
        # THe button down has a delay... so this is on top of that.
        return await google_home("tell roomba to go home")

    return await google_home("start vacuuming")


async def on_ikea_move1(client, payload):
    """
    '{"battery":100,"illuminance_above_threshold":false,"linkquality":84,"occupancy":true,"requested_brightness_level":254,"requested_brightness_percent":100,"update":{"state":"idle"},"update_available":false}
    """
    global ikea_move1_last
    ikea_move1_last = payload
    await trio.sleep(5)
    if ikea_move1_last is not payload:
        _log("Cancel move ")
        return
    _log("go with move " + str(payload))


async def google_home(command, broadcast=False, converse=False, cast=False):
    """
    Send a command to Google home via assistant relay.
    """
    _log("Sending to Google " + command)
    payload = {
        "user": "adi",
        "command": command,
        "broadcast": broadcast,
        "converse": converse,
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_URL + "/assistant",
                json=payload,
                # It can take a long time for assitant relay to respond.
                timeout=30,
                )
        _log("Response from Google " + str(response.text))
    except Exception as error:
        _log("Faild to cast:\n" + str(error))
        return

    if not cast:
        return

    payload = {
        "device": "Office speaker",
        "source": "{}{}".format(GOOGLE_URL, response.json()['audio']),
        "type": "remote",
        }

    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                GOOGLE_URL + "/cast",
                json=payload,
                # It can take a long time for assitant relay to respond.
                timeout=30,
                )
        _log("Response from cast " + str(r.text))
    except Exception as error:
        _log("Faild to cast:\n" + str(error))


def _log(text):
    print(text, file=sys.stderr)


_log("Starting")
tasmota = TasmotaAdapter(MQTT_ADDRESS, BRIDGE_NAME, get_sensors)
tasmota.loop()
_log("Finished")
