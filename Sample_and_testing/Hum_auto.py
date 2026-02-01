import sys
import asyncio

# 1. FORCE THE PATH
site_packages = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

# 2. LOAD THE SCANNER
try:
    # Importing the base BleakScanner as a fallback since SwitchBotScanner 
    # is often just a wrapper around it in this version
    from bleak import BleakScanner
    print("✅ Bluetooth Scanner Ready.")
except ImportError:
    print("❌ Bleak missing. Run: /usr/local/bin/python3 -m pip install bleak")
    sys.exit(1)

# 3. YOUR DEVICE ID
MY_UUID = ""

def decode_switchbot_data(adv_data):
    """
    Manually decodes the SwitchBot advertising packets.
    """
    # Look into Manufacturer Data (SwitchBot ID is 2409 / 0x0969)
    # This is a fallback if the high-level library isn't parsing correctly
    for data in adv_data.manufacturer_data.values():
        if len(data) >= 6:
            # SwitchBot Meter data format:
            # Byte 4: Humidity (0-100)
            # Byte 3: Temperature (with signs/flags)
            temp = data[3] & 0x7F
            is_negative = not (data[3] & 0x80)
            humidity = data[4] & 0x7F
            return temp if not is_negative else -temp, humidity
    return None, None

async def main():
    print(f"🚀 Searching for Meter: {MY_UUID}")
    
    # We use a discovery loop since 'start' failed
    while True:
        # Scan for a short burst
        device = await BleakScanner.find_device_by_address(MY_UUID, timeout=10.0)
        
        if device:
            # Get the advertisement data
            # Note: find_device_by_address on Mac sometimes doesn't return adv_data
            # so we use the scanner directly for better reliability
            scanner = BleakScanner()
            devices_and_adv = await scanner.discover(return_adv=True, timeout=5.0)
            
            if MY_UUID in devices_and_adv:
                d, adv = devices_and_adv[MY_UUID]
                
                # Check Service Data (The most common place for SwitchBot readings)
                for uuid, data in adv.service_data.items():
                    if len(data) >= 6:
                        # Standard SwitchBot Decoding
                        temp = (data[4] & 0x7F) + (data[3] / 10.0)
                        humidity = data[5] & 0x7F
                        print(f"--- [REAL-TIME DATA] ---")
                        print(f"Humidity:    {humidity}%")
                        print(f"Temperature: {temp}°C")
                        print(f"------------------------\n")
        
        await asyncio.sleep(2) # Wait before next scan to save Mac battery

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopping monitor...")
