import sys
import asyncio
import time
import csv
import os
from datetime import datetime

# 1. PATH FIX FOR MAC MINI
site_packages = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

from bleak import BleakClient, BleakScanner
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

# --- CONFIGURATION ---
MY_UUID = "Your UUID"
MEROSS_EMAIL = "Your_Email"
MEROSS_PASS = "Your_Password" 
TARGET_DEVICE_NAME = "Bed Plug"

HUMIDITY_THRESHOLD = 50.0   
BASE_DIR = "/Volumes/Studies/Smart Room/Log_File/"

# --- LOGIC CONSTANTS ---
MIN_RUN_TIME = 5 * 3600        
COOLDOWN_TIME = 1.5 * 3600     
RETRIGGER_RUN_TIME = 1 * 3600  
MAX_DAILY_RUN = 7 * 3600       

# --- STATE & ANALYTICS ---
last_turn_on_time = None
last_turn_off_time = None
total_daily_runtime = 0
current_day = datetime.now().date()
needs_forced_on = True 

hourly_readings = []
last_log_time = time.time()
daily_history = [] 

async def log_data(humidity):
    global last_log_time, hourly_readings, daily_history
    hourly_readings.append(humidity)
    
    # Check if an hour has passed
    if time.time() - last_log_time >= 3600:
        now_dt = datetime.now()
        avg_h = sum(hourly_readings) / len(hourly_readings)
        daily_history.append(avg_h)
        if len(daily_history) > 24: daily_history.pop(0) 
        overall_avg = sum(daily_history) / len(daily_history)
        
        # --- DYNAMIC FILE NAMING ---
        # Format: humidity_stats_2026-01-31_Saturday.csv
        date_str = now_dt.strftime("%Y-%m-%d")
        day_name = now_dt.strftime("%A")
        log_filename = f"{BASE_DIR}humidity_stats_{date_str}_{day_name}.csv"
        
        file_exists = os.path.isfile(log_filename)
        with open(log_filename, mode='a', newline='') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Timestamp", "Day", "Hourly_Avg", "Rolling_24h_Avg", "Total_Runtime_Sec"])
            writer.writerow([now_dt.strftime("%H:%M"), day_name, round(avg_h, 2), round(overall_avg, 2), round(total_daily_runtime, 2)])
        
        print(f"📂 Data saved to: {os.path.basename(log_filename)}")
        last_log_time = time.time()
        hourly_readings = []

async def main():
    global last_turn_on_time, last_turn_off_time, total_daily_runtime, current_day, needs_forced_on
    print("🚀 Starting Smart Room Automation v2.3...")

    # Initialize Meross
    http_api_client = await MerossHttpClient.async_from_user_password(
        email=MEROSS_EMAIL, password=MEROSS_PASS, api_base_url="https://iot.meross.com", ssl=False
    )
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    await manager.async_device_discovery()
    plug = next((d for d in manager.find_devices() if d.name == TARGET_DEVICE_NAME), None)

    async def toggle_logic(humidity):
        global last_turn_on_time, last_turn_off_time, total_daily_runtime, current_day, needs_forced_on
        now = time.time()
        today = datetime.now().date()

        if today != current_day:
            total_daily_runtime = 0
            current_day = today
            needs_forced_on = True # Reset force-sync for the new day
            print(f"📅 Resetting for {today.strftime('%A')}")

        await plug.async_update()
        is_on = plug.is_on

        if is_on:
            if last_turn_on_time is None: last_turn_on_time = now
            if needs_forced_on:
                print(f"⚠️ Syncing: Sending FORCE ON to {plug.name}...")
                await plug.async_turn_on()
                needs_forced_on = False

            run_duration = now - last_turn_on_time
            required = MIN_RUN_TIME if (total_daily_runtime < MIN_RUN_TIME) else RETRIGGER_RUN_TIME
            
            if run_duration >= required or (total_daily_runtime + run_duration) >= MAX_DAILY_RUN:
                print(f"🛑 Stopping Cycle. Total runtime: {total_daily_runtime/3600:.2f}h")
                await plug.async_turn_off()
                last_turn_off_time = now
                total_daily_runtime += run_duration
                last_turn_on_time = None
            return

        if not is_on:
            needs_forced_on = True 
            if total_daily_runtime >= MAX_DAILY_RUN: return
            if last_turn_off_time and (now - last_turn_off_time < COOLDOWN_TIME): return
            if humidity >= HUMIDITY_THRESHOLD:
                print(f"⚠️ Humidity {humidity}% high. Starting cycle...")
                await plug.async_turn_on()
                last_turn_on_time = now
                needs_forced_on = False

    def detection_callback(device, advertisement_data):
        if device.address == MY_UUID:
            for uuid, data in advertisement_data.service_data.items():
                if len(data) >= 6:
                    humidity = data[5] & 0x7F
                    temp = (data[4] & 0x7F) + (data[3] / 10.0)
                    print(f"📊 Live -> {humidity}% | {temp}°C | Runtime: {total_daily_runtime/3600:.2f}h")
                    asyncio.create_task(toggle_logic(humidity))
                    asyncio.create_task(log_data(humidity))

    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()

    while True:
        try:
            async with BleakClient(MY_UUID, timeout=20.0) as client:
                print(f"✅ LINK ACTIVE. Logic Engaged.")
                while client.is_connected:
                    await asyncio.sleep(10)
        except Exception:
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())