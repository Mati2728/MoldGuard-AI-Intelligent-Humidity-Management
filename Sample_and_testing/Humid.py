import asyncio
from bleak import BleakScanner

async def find_uuid_by_mac():
    # Your SwitchBot MAC Address
    TARGET_MAC = "".lower()
    
    print(f"Searching for SwitchBot with MAC: {TARGET_MAC}...")
    devices = await BleakScanner.discover(timeout=10.0, return_adv=True)
    
    for d, adv in devices.values():
        # SwitchBot puts the MAC address in the Manufacturer Data (ID 2409)
        # and sometimes in the Service Data. We check both.
        found = False
        
        # Check Manufacturer Data
        for company_id, data in adv.manufacturer_data.items():
            if TARGET_MAC in data.hex():
                found = True
        
        # Check Service Data
        for uuid, data in adv.service_data.items():
            if TARGET_MAC in data.hex():
                found = True

        if found or (d.name and "WoSensor" in d.name):
            print(f"\n✅ MATCH FOUND!")
            print(f"Name: {d.name}")
            print(f"MAC Address detected: {TARGET_MAC}")
            print(f"Use this UUID in your next script: {d.address}")
            return d.address

    print("\n❌ Could not find a match. Make sure the meter is close and phone BT is OFF.")
    return None

if __name__ == "__main__":
    asyncio.run(find_uuid_by_mac())
