# Hue Thief Skyconnect


Factory reset Philips Hue bulbs using a SkyConnect USB Stick
Heavily inspired by https://github.com/vanviegen/hue-thief but also includes a lot of changes.

## Installation

Make sure you have python v3 and pip. (`sudo apt-get install python3-pip`)

```sh
git clone https://github.com/johnneerdael/hue-thief-skyconnect.git
cd hue-thief-skyconnect
pip3 install --user -r requirements.txt
```

## Usage

Bring the bulb(s) you want to factory reset close to your EZSP device. Shutdown any other applications (home assistant, perhaps?) that may be using the EZSP device. Power on the bulb(s) and immediately:

```sh
python3 hue-thief /dev/ttyUSB0
```

`/dev/ttyUSB0` should be your EZSP device. You should have full permissions on this device file.

'''sh
sudo usermod -a -G dialout $USER
sudo chmod 666 /dev/ttyUSB0
'''


## Problems

I will not be held responsible if you brick any hardware or do other awful things with this. On the bright side: I really don't see how that could ever happen, but still...

This script is kind of a hack, as it tries to implement about a zillion layers of Zigbee protocol in just a few lines of code. :-) So things will only work if everything goes *exactly* according to plan.

If no devices are found, there is no blinking or the factory reset doesn't work, the generated `log.pcap` file should be the first place to look for a clue. (Wireshark has decent Zigbee analyzers, though the ZLL commissioning part is still missing.)

