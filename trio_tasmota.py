#
# Low level of MQTT with trio.
#
# Also contains an addapter for Tasmota messages designed to be used for
# automation
#
import json
import socket
import sys
import uuid

import paho.mqtt.client as mqtt
import trio


class TrioMQTT:
    """
    Low-level handling for MQTT.

    It will call the callbacks with self instead for the low-level client.

    This is designed to be used with any MQTT server, not only with Tasmota.
    """

    def __init__(self, address, port, on_connect, on_message, on_disconnect):
        self._address = address
        self._client = mqtt.Client()
        self._sock = None
        self._nursery = None
        self._event_large_write = trio.Event()

        self._connect_callback = on_connect
        self._message_callback = on_message
        self._disconnect_callback = on_disconnect

        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

        self._client.on_socket_open = self._on_socket_open
        self._client.on_socket_register_write = self._on_socket_register_write
        self._client.on_socket_unregister_write = self._on_socket_unregister_write

    async def start(self):
        async with trio.open_nursery() as nursery:
            self._nursery = nursery

            self._client.connect(self._address, 1883, 60)

            nursery.start_soon(self._read_loop)
            nursery.start_soon(self._write_loop)
            nursery.start_soon(self._misc_loop)

        self._client.disconnect()

    def subscribe(self, topic):
        self._client.subscribe(topic)

    async def publish(self, topic, message):
        self._client.publish(topic, message, qos=1)

    def _on_connect(self, client, userdata, flags, rc):
        self._nursery.start_soon(self._connect_callback, self, userdata, flags, rc)

    def _on_disconnect(self, client, userdata, rc):
        self._nursery.start_soon(self._disconnect_callback, self, userdata, rc)

    def _on_message(self, client, userdata, msg):
        self._nursery.start_soon(self._message_callback, self, userdata, msg)

    async def _read_loop(self):
        while True:
            await trio.lowlevel.wait_readable(self._sock)
            self._client.loop_read()

    async def _write_loop(self):
        while True:
            await self._event_large_write.wait()
            await trio.lowlevel.wait_writable(self._sock)
            self._client.loop_write()

    async def _misc_loop(self):
        _log("misc_loop started")
        while self._client.loop_misc() == mqtt.MQTT_ERR_SUCCESS:
            await trio.sleep(1)
        _log("misc_loop finished")

    def _on_socket_open(self, client, userdata, sock):
        _log("Socket opened")
        self._sock = sock
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 2048)

    def _on_socket_register_write(self, client, userdata, sock):
        _log("large write request")
        self._event_large_write.set()

    def _on_socket_unregister_write(self, client, userdata, sock):
        _log("finished large write")
        self._event_large_write = trio.Event()


def _get_topics(bridge_name):
    """
    Retrun the main topics for Tasmota
    """
    return {
        "tele/{}/SENSOR".format(bridge_name): _on_sensor,
        "tele/{}/RESULT".format(bridge_name): _on_result,
        "stat/{}/RESULT".format(bridge_name): _on_result,
    }


async def _on_sensor(client, payload, callbacks):
    """
    Called when a sensor got something for us.
    """
    for target_id, value in payload["ZbReceived"].items():
        # See if the sensor is registred.
        for sensor_id, action in callbacks.items():
            if sensor_id != target_id:
                continue
            await action(client, value)


async def _on_result(client, payload, callbacks):
    """
    Called when we got a response for an action.

    For now does nothing as we just use general log.
    """


class TasmotaAdapter:
    """
    Connects to Tasmota MQTT and subscribe for topics.

    It will call `sensors` callback on events.
    """

    def loop(self):
        trio.run(self._trio_mqtt.start)
        _log("Disconnected")

    def __init__(self, address, bridge_name, sensors):

        self._topics = _get_topics(bridge_name)
        self._sensor_callbacks = sensors()

        self._trio_mqtt = TrioMQTT(
            address=address,
            port=1883,
            on_connect=self.on_connect,
            on_message=self.on_message,
            on_disconnect=self.on_disconnect,
        )

    async def on_connect(self, client, userdata, flags, rc):
        _log("Subscribing")
        for topic in self._topics.keys():
            client.subscribe(topic)

    async def on_message(self, client, userdata, msg):
        _log("Got message on {}: {}".format(msg.topic, msg.payload))
        action = self._topics.get(msg.topic, None)
        if not action:
            return

        payload = json.loads(msg.payload)
        await action(client, payload, self._sensor_callbacks)

    async def on_disconnect(self, client, userdata, rc):
        _log("Disconnect result {}".format(rc))


async def zb_power(client, device, state):
    """
    Send power command for Tasmota `device`.
    """
    payload = {
        "Send": {"Power": state},
    }
    await zb_send(client, device, payload)


async def zb_dim(client, device, value):
    payload = {
        "Send": {"Dimmer": int(value)},
    }
    await zb_send(client, device, payload)


async def zb_send(client, device, payload):
    """
    Topic = cmnd/ZigbeeGateway/ZbSend
    Payload = {"Device":"0x1234","Send":{"Power":0}} or {"Device":"0x1234","Write":{"Power":0}}
    """
    command = {
        "Device": device,
    }
    command.update(payload)
    _log("Sending to bridge: {}".format(command))
    await client.publish(
        "cmnd/{}/ZbSend".format(BRIDGE_NAME),
        json.dumps(command),
    )


def _log(text):
    print(text, file=sys.stderr)
