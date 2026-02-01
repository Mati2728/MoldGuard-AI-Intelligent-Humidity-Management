import asyncio
import sys

# 1. FORCE THE PATH (For Mac Mini Python 3.14)
site_packages = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

# --- YOUR DETAILS ---
EMAIL = ""
PASSWORD = "" 
API_URL = "https://iot.meross.com"

async def main():
    print(f"Logging into Meross account: {EMAIL}...")
    
    try:
        # 2. AUTHENTICATE
        http_api_client = await MerossHttpClient.async_from_user_password(
            email=EMAIL, 
            password=PASSWORD, 
            api_base_url=API_URL,
            ssl=False 
        )

        # 3. INITIALIZE MANAGER
        manager = MerossManager(http_client=http_api_client)
        await manager.async_init()

        # 4. DISCOVER DEVICES
        print("Searching for devices...")
        await manager.async_device_discovery()
        
        # 5. TARGET "Bed Plug" SPECIFICALLY
        plugs = manager.find_devices()
        target_plug = next((d for d in plugs if d.name == "Bed Plug"), None)

        if not target_plug:
            print("❌ 'Bed Plug' not found. Found these instead:")
            for d in plugs:
                print(f" - {d.name}")
        else:
            # Sync the latest state from the cloud
            await target_plug.async_update()
            
            # Use the updated attribute .is_on
            current_status = "ON" if target_plug.is_on else "OFF"
            print(f"\n✅ Found Device: {target_plug.name}")
            print(f"Current Status: {current_status}")

            if target_plug.is_on:
                print(f"Sending 'TURN OFF' command to {target_plug.name}...")
                await target_plug.async_turn_off()
                print("✅ Command sent. The plug should click OFF now.")
            elif target_plug.is_off:
                print(f"Sending 'TURN ON' command to {target_plug.name}...")
                await target_plug.async_turn_on()
                print("✅ Command sent. The plug should click ON now.")
            else:
                print(f"The {target_plug.name} is already OFF.")

        # 6. CLEANUP
        manager.close()
        await http_api_client.async_logout()

    except Exception as e:
        print(f"\n❌ Critical Error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nScript stopped.")
