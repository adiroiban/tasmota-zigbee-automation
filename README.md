# tasmota-zigbee-automation
Home automation based on Tasmota zibgee bridge and Python3.

This is the code I use for my home automation.

It is based on zigbee.

Designed to be executed on RPI, with mosquito and assistant relay.

For now, I have a Sonnof zigbee-wifi bridge.

The plan is to move to an USB zibgee stick,
but now I have only a cheap CC2531 USB dongle that is trash/not usable.

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