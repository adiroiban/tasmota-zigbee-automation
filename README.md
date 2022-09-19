# tasmota-zigbee-automation
Home automation based on Tasmota zibgee bridge and Python3.

This is the code I use as a test for my home automation.

It is based on zigbee.

Designed to be executed on RPI, with mosquito and assistant relay.

It is designed to be used with Sonnof zigbee-wifi bridge and Sonnof native MQTT interface.

There is not much here as I am not using Home Assistant, so this is no longer used.

This is still useful for very simple automation or industrial automation, when you don't want the full power of Home Assistant
or want to run it on a low-power device.

This is carpe-diem development.
No automated test.
No regressions.
No worries.
Hack for fun.


# Install

Python environment:

    virtualenv venv
    . venv/bin/activate
    pip install -r requiremetns.txt

Systemd integration:

    # Edit systemd unit file
    sudo cp tasmota-zigbee-automation.service /etc/systemd/system/
    sudo systemctl start tasmota-zigbee-automation
    sudo systemctl status tasmota-zigbee-automation
