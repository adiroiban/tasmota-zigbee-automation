#
# Personal automation based on Tasmota MQTT and Paho and Assitant relay.
#
import json
import sys
import time

import trio

from trio_tasmota import TasmotaAdapter, zb_dim

BRIDGE_NAME = "tasmota_zbBridge"
HOST = "172.19.0.31"
MQTT_ADDRESS = HOST
GOOGLE_URL = "http://{}:3000".format(HOST)

LITTER_BUTTON = "0xF2F3"
LIGHT_SENSOR = "0x961B"
LIGHT_STAIRS = "0x37CA"


def get_sensors():
    return {
        LITTER_BUTTON: on_ikea_action1,
        LIGHT_SENSOR: on_light_sensor,
    }


ikea_action1_down_start = 0
ikea_move1_last = 0


async def on_light_sensor(client, payload):
    """ """
    await zb_dim(client, LIGHT_STAIRS, 12)


async def on_ikea_action1(client, payload):
    """ """
    global ikea_action1_down_start
    if "action" not in payload:
        return

    if payload["action"] == "on":
        return await google_home("start vacuuming the hall")

    if payload["action"] == "brightness_move_up":
        # Long press started.
        ikea_action1_down_start = time.time()
        return

    # Most probabling long press released.
    duration = time.time() - ikea_action1_down_start

    if duration > 2:
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


async def google_home(command, broadcast=False, converse=False):
    """
    Send a command to Google home via assistant relay
    """
    _log("Sending to Google " + command)
    return
    payload = {
        "user": "adi",
        "command": command,
        "broadcast": broadcast,
        "converse": coverse,
    }
    payload.update(command)
    r = httpx.post(GOOGLE_URL + "/assistant", json=payload)
    _log("Response from Google " + str(r.text))


def _log(text):
    print(text, file=sys.stderr)


_log("Starting")
TasmotaAdapter(MQTT_ADDRESS, BRIDGE_NAME, get_sensors).loop()
_log("Finished")
