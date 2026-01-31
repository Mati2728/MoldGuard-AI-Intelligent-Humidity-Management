import sys
import asyncio

# 1. PATH FIX
site_packages = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

from bleak import BleakClient, BleakScanner
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

# --- CONFIGURATION ---
MY_UUID = ""
MEROSS_EMAIL = ""
MEROSS_PASS = "" 
TARGET_DEVICE_NAME = ""

HUMIDITY_ON = 60.0   
HUMIDITY_OFF = 50.0  

async def main():
    print("🚀 Starting Final Resolved Automation...")
    
    # 2. CONNECT TO MEROSS
    http_api_client = await MerossHttpClient.async_from_user_password(
        email=MEROSS_EMAIL, password=MEROSS_PASS, api_base_url="https://iot.meross.com", ssl=False
    )
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    await manager.async_device_discovery()
    
    # Find the plug by name
    all_plugs = manager.find_devices()
    plug = next((d for d in all_plugs if d.name == TARGET_DEVICE_NAME), None)
    
    if not plug:
        print(f"❌ Error: {TARGET_DEVICE_NAME} not found.")
        return
    print(f"✅ Meross Ready: {plug.name}")

    # 3. DEFINE THE PLUG ACTION
    async def toggle_plug(humidity):
        # We force the command regardless of what the script 'thinks' the state is
        if humidity >= HUMIDITY_ON:
            print(f"⚠️ Humidity {humidity}% high! Sending FORCE ON to {plug.name}...")
            await plug.async_turn_on()
        elif humidity <= HUMIDITY_OFF:
            print(f"✅ Humidity {humidity}% safe. Sending FORCE OFF to {plug.name}...")
            await plug.async_turn_off()

    # 4. DETECTION CALLBACK
    def detection_callback(device, advertisement_data):
        if device.address == MY_UUID:
            for uuid, data in advertisement_data.service_data.items():
                if len(data) >= 6:
                    humidity = data[5] & 0x7F
                    temp = (data[4] & 0x7F) + (data[3] / 10.0)
                    print(f"📊 Live Data -> Humidity: {humidity}% | Temp: {temp}°C")
                    
                    # Call the plug toggle directly
                    loop = asyncio.get_event_loop()
                    loop.create_task(toggle_plug(humidity))

    # 5. START SCANNER & KEEP-ALIVE CONNECTION
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    while True:
        try:
            async with BleakClient(MY_UUID, timeout=20.0) as client:
                print(f"✅ LINK ACTIVE. Keeping meter awake...")
                while client.is_connected:
                    await asyncio.sleep(10)
        except Exception as e:
            print(f"❌ Connection dropped: {e}. Retrying...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping Automation.")
