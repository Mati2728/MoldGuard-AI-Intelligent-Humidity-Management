

import sys
import asyncio
import time
import csv
import os
from datetime import datetime

# 1. ENVIRONMENT SETUP
site_packages = "/Library/Frameworks/Python.framework/Versions/3.14/lib/python3.14/site-packages"
if site_packages not in sys.path:
    sys.path.append(site_packages)

from bleak import BleakClient, BleakScanner
from meross_iot.http_api import MerossHttpClient
from meross_iot.manager import MerossManager

# --- ⚙️ USER CONFIGURATION ---
MY_UUID = ""
MEROSS_EMAIL = ""
MEROSS_PASS = "" 
TARGET_DEVICE_NAME = "Bed Plug"

# Logic Thresholds
PRIMARY_THRESHOLD = 65.0      
SECONDARY_THRESHOLD = 55.0    
BASE_DIR = "/Users/ganeshbabukarunanithi/scripts/Log_Files/"

# --- ⏱️ INTERVAL CONSTANTS (The Source of Truth) ---
PRIMARY_DURATION = 4 * 3600      # 18000 Seconds
SECONDARY_DURATION = 1 * 3600    # 3600 Seconds
COOLDOWN_DURATION = 2.5 * 3600   # 5400 Seconds
MAX_DAILY_TOTAL = 6 * 3600       # 25200 Seconds

data_queue = asyncio.Queue()

def get_today_csv_path():
    return f"{BASE_DIR}MoldGuard_{datetime.now().strftime('%Y-%m-%d_%A')}.csv"

def init_csv_brain():
    """Ensures the CSV exists with the correct columns."""
    path = get_today_csv_path()
    if not os.path.exists(path):
        with open(path, mode='w', newline='') as f:
            fieldnames = [
                "Timestamp", "Event", "Humidity", 
                "Duration_Logged", "Daily_Total_Accumulated", 
                "Avg_Humidity", "Notes"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
        print(f"📝 BRAIN CREATED: {os.path.basename(path)}")

async def log_to_csv(event, humidity, duration=0, daily_total=0, avg_hum=0, notes=""):
    """Writes to disk immediately."""
    path = get_today_csv_path()
    with open(path, mode='a', newline='') as f:
        fieldnames = [
            "Timestamp", "Event", "Humidity", 
            "Duration_Logged", "Daily_Total_Accumulated", 
            "Avg_Humidity", "Notes"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writerow({
            "Timestamp": datetime.now().strftime("%H:%M:%S"),
            "Event": event, 
            "Humidity": round(humidity, 1),
            "Duration_Logged": int(duration),
            "Daily_Total_Accumulated": round(daily_total, 2),
            "Avg_Humidity": round(avg_hum, 1),
            "Notes": notes
        })
        f.flush()
        os.fsync(f.fileno())

def read_brain_state():
    """
    Reads the CSV to calculate:
    1. Total runtime used today.
    2. Has the Primary run happened?
    3. What was the LAST event and WHEN did it happen?
    """
    path = get_today_csv_path()
    if not os.path.exists(path): return 0, False, None, 0, 0

    total_time = 0
    primary_done = False
    last_event = None
    last_event_timestamp = 0
    last_event_humidity = 0

    try:
        with open(path, mode='r') as f:
            reader = list(csv.DictReader(f))
            for row in reader:
                # Accumulate Time
                if "STOP" in row['Event']:
                    run_time = float(row['Duration_Logged'])
                    total_time += run_time
                    # Check against CONSTANT for Primary detection
                    if run_time >= (PRIMARY_DURATION - 300):
                        primary_done = True
                
                # Track Last Event
                last_event = row['Event']
                last_event_humidity = float(row['Humidity'])
                dt = datetime.strptime(row['Timestamp'], "%H:%M:%S")
                last_event_timestamp = datetime.now().replace(hour=dt.hour, minute=dt.minute, second=dt.second).timestamp()

    except Exception:
        return 0, False, None, 0, 0

    return total_time, primary_done, last_event, last_event_timestamp, last_event_humidity

async def worker(plug):
    print("🤖 CSV BRAIN: ONLINE")
    init_csv_brain()

    while True:
        humidity = await data_queue.get()
        now = time.time()
        
        # 1. READ THE BRAIN (Disk Read)
        daily_total, primary_done, last_event, last_ts, last_hum = read_brain_state()
        
        # 2. DETERMINE STATE
        if last_event is None or "BREAK_ENDED" in last_event or "STOP" in last_event:
            # Possible States: IDLE or COOLDOWN?
            
            # Check if we just stopped and need a break
            if last_event and "STOP" in last_event:
                time_since_stop = now - last_ts
                
                # --- COOLDOWN LOGIC ---
                if time_since_stop < COOLDOWN_DURATION:
                    remaining = COOLDOWN_DURATION - time_since_stop
                    
                    # If this is the *first* moment of cooldown detection (not logged yet), log start
                    # (Wait, user wants start/end logged. We rely on STOP event as the start of break)
                    
                    sys.stdout.write(f"\r❄️ COOLDOWN: {remaining/60:.1f}m / {COOLDOWN_DURATION/60:.0f}m left | Break Start Hum: {last_hum}%   ")
                    sys.stdout.flush()
                else:
                    # Break is Over. Did we log it?
                    # We check if the last event was STOP. If yes, we need to log BREAK_ENDED now.
                    print(f"\n✅ BREAK ENDED. Duration: {time_since_stop/60:.1f}m")
                    avg_hum = (last_hum + humidity) / 2
                    await log_to_csv("BREAK_ENDED", humidity, duration=time_since_stop, daily_total=daily_total, avg_hum=avg_hum, notes="Cooldown Complete")
                    continue # Loop again to refresh state as IDLE

            # --- IDLE LOGIC ---
            # If last event was BREAK_ENDED or None, we are IDLE
            if last_event is None or "BREAK_ENDED" in last_event:
                if daily_total >= MAX_DAILY_TOTAL:
                    sys.stdout.write(f"\r🛑 DAILY CAP HIT: {daily_total/3600:.2f}/{MAX_DAILY_TOTAL/3600:.0f}h   ")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r👀 IDLE: {humidity}% | Primary Done: {primary_done}   ")
                    sys.stdout.flush()
                    
                    # TRIGGERS
                    target_duration = 0
                    mode = ""
                    
                    if not primary_done and humidity >= PRIMARY_THRESHOLD:
                        target_duration = PRIMARY_DURATION
                        mode = "PRIMARY"
                    elif humidity >= SECONDARY_THRESHOLD:
                        target_duration = SECONDARY_DURATION
                        mode = "SECONDARY"
                    
                    if mode:
                        print(f"\n⚡ TRIGGER: {mode} ({humidity}%). Starting Plug.")
                        await plug.async_turn_on()
                        await log_to_csv(f"START_{mode}", humidity, notes=f"Target: {target_duration}s")

        # --- RUNNING LOGIC ---
        elif "START" in last_event:
            # We are inside a run
            elapsed = now - last_ts
            
            # Determine Target based on the Event Name in CSV
            target_time = PRIMARY_DURATION if "PRIMARY" in last_event else SECONDARY_DURATION
            
            remaining = target_time - elapsed
            
            # Console Update
            sys.stdout.write(f"\r⏳ RUNNING: {elapsed/60:.1f}m / {target_time/60:.0f}m | Hum: {humidity}%   ")
            sys.stdout.flush()

            # CHECK LIMITS
            if elapsed >= target_time or (daily_total + elapsed) >= MAX_DAILY_TOTAL:
                print(f"\n🛑 STOPPING. Target Reached.")
                await plug.async_turn_off()
                
                # Log STOP
                # New Total = Old Total (from CSV) + Elapsed
                new_total = daily_total + elapsed
                
                await log_to_csv("STOP_MACHINE", humidity, duration=elapsed, daily_total=new_total, notes=f"Run Finished")

        data_queue.task_done()

async def main():
    print(f"🚀 MoldGuard-AI v8.0: Stateless CSV Brain")
    
    http_api_client = await MerossHttpClient.async_from_user_password(
        email=MEROSS_EMAIL, password=MEROSS_PASS, api_base_url="https://iot.meross.com", ssl=False
    )
    manager = MerossManager(http_client=http_api_client)
    await manager.async_init()
    await manager.async_device_discovery()
    plug = next((d for d in manager.find_devices() if d.name == TARGET_DEVICE_NAME), None)

    if not plug: return

    def ble_callback(device, advertisement_data):
        if device.address == MY_UUID:
            for uuid, data in advertisement_data.service_data.items():
                if len(data) >= 6:
                    humidity = data[5] & 0x7F
                    data_queue.put_nowait(humidity)

    scanner = BleakScanner(detection_callback=ble_callback)
    await scanner.start()
    await worker(plug)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting.")
