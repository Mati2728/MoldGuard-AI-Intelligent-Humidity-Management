import sys
import asyncio
import time
import csv
import os
import shutil
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
TARGET_DEVICE_NAME = ""

# Logic Thresholds
PRIMARY_THRESHOLD = 65.0      
SECONDARY_THRESHOLD = 57.0    
BASE_DIR = "/Log_Files/"

# --- ⏱️ INTERVAL CONSTANTS ---
PRIMARY_DURATION = 5 * 3600      
SECONDARY_DURATION = 1.5 * 3600    
COOLDOWN_DURATION = 2.5 * 3600   
MAX_DAILY_TOTAL = 7 * 3600       

data_queue = asyncio.Queue()

CSV_HEADERS = [
    "Session_ID", "Date", "Start_Time", "End_Time", 
    "Event_Type", "Status", "Start_Hum", "End_Hum", 
    "Target_Min", "Actual_Min", "Actual_Hours", 
    "Daily_Cumulative_Hours", "Notes"
]

emergency_ram_backup = {} 

def get_today_csv_path():
    return f"{BASE_DIR}MoldGuard_{datetime.now().strftime('%Y-%m-%d_%A')}.csv"

def ensure_file_integrity():
    path = get_today_csv_path()
    if not os.path.exists(path):
        print(f"\n⚠️ CRITICAL: CSV DELETED. REBUILDING FROM BACKUP...")
        create_fresh_file(path)
        write_system_note("FILE_RESTORED", "Rebuilt from RAM")
        if emergency_ram_backup:
            restore_backup_row(emergency_ram_backup)
        return

    try:
        with open(path, 'r') as f:
            if not f.readline().startswith("Session_ID"): raise ValueError
    except:
        create_fresh_file(path)
        if emergency_ram_backup: restore_backup_row(emergency_ram_backup)

def create_fresh_file(path):
    with open(path, mode='w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        f.flush()
        os.fsync(f.fileno())

def write_system_note(event_type, note):
    path = get_today_csv_path()
    with open(path, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow({
            "Session_ID": "SYSTEM",
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "Start_Time": datetime.now().strftime("%H:%M:%S"),
            "Event_Type": event_type,
            "Notes": note
        })

def restore_backup_row(row_data):
    path = get_today_csv_path()
    row_data['Notes'] = f"{row_data.get('Notes','')} [RESTORED]"
    with open(path, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row_data)
        f.flush()
        os.fsync(f.fileno())

def get_brain_decision_data():
    ensure_file_integrity()
    path = get_today_csv_path()
    daily_total = 0
    primary_done = False
    last_valid_row = None
    
    try:
        with open(path, mode='r') as f:
            reader = list(csv.DictReader(f))
            for row in reader:
                if row['Session_ID'] == "SYSTEM": continue
                last_valid_row = row 
                
                # Accumulate Valid Hours
                status = row.get('Status')
                if status in ['COMPLETED', 'CRASHED_OVERTIME', 'CRASHED_RESUMED', 'MIDNIGHT_STOP', 'DAILY_LIMIT_STOP']:
                    try: daily_total += (float(row.get('Actual_Hours', 0)) * 3600)
                    except: pass
                
                # Check Primary
                if "PRIMARY" in row.get('Event_Type', '') and status == 'COMPLETED':
                    try:
                        if (float(row.get('Actual_Hours', 0)) * 3600) >= (PRIMARY_DURATION - 300):
                            primary_done = True
                    except: pass
    except: return 0, False, None

    return daily_total, primary_done, last_valid_row

def write_new_run_to_disk(event_type, humidity, target_sec, daily_total_prev, is_capped=False):
    global emergency_ram_backup
    ensure_file_integrity()
    path = get_today_csv_path()
    session_id = int(time.time())
    
    note_text = "Started"
    if is_capped: note_text = f"Target Capped by Daily Limit"
    
    row_data = {
        "Session_ID": session_id,
        "Date": datetime.now().strftime("%Y-%m-%d"),
        "Start_Time": datetime.now().strftime("%H:%M:%S"),
        "End_Time": "...",
        "Event_Type": event_type,
        "Status": "RUNNING",
        "Start_Hum": round(humidity, 1),
        "End_Hum": 0,
        "Target_Min": int(target_sec / 60),
        "Actual_Min": 0,
        "Actual_Hours": 0,
        "Daily_Cumulative_Hours": round(daily_total_prev / 3600, 4),
        "Notes": note_text
    }
    
    emergency_ram_backup = row_data.copy()

    with open(path, mode='a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writerow(row_data)
        f.flush()
        os.fsync(f.fileno())
    
    return session_id

def update_disk_row(session_id, **updates):
    global emergency_ram_backup
    ensure_file_integrity()
    path = get_today_csv_path()
    temp_path = path + ".tmp"
    
    if emergency_ram_backup and str(emergency_ram_backup.get('Session_ID')) == str(session_id):
        for k, v in updates.items(): emergency_ram_backup[k] = v

    try:
        with open(path, 'r') as infile, open(temp_path, 'w', newline='') as outfile:
            reader = csv.DictReader(infile)
            writer = csv.DictWriter(outfile, fieldnames=CSV_HEADERS)
            writer.writeheader()
            for row in reader:
                if str(row['Session_ID']) == str(session_id):
                    for k, v in updates.items(): row[k] = v
                writer.writerow(row)
        shutil.move(temp_path, path)
        os.sync()
    except: pass

async def startup_check(plug):
    print("🕵️ CHECKING DISK STATUS...")
    daily_total, _, last_row = get_brain_decision_data()
    
    if not last_row: return "IDLE", 0, 0, 0

    # 1. ZOMBIE CHECK
    if last_row.get('Status') == 'RUNNING':
        print(f"⚠️ FOUND UNFINISHED SESSION: {last_row['Session_ID']}")
        st_obj = datetime.strptime(last_row['Start_Time'], "%H:%M:%S")
        start_ts = datetime.now().replace(hour=st_obj.hour, minute=st_obj.minute, second=st_obj.second).timestamp()
        
        elapsed = time.time() - start_ts
        target_sec = float(last_row['Target_Min']) * 60
        
        # --- CRASH LOGIC UPDATE: DAILY LIMIT ---
        # Even if it's not overtime for the *session*, is it overtime for the *day*?
        if (daily_total + elapsed) > MAX_DAILY_TOTAL:
            print(f"🚨 CRASHED & EXCEEDED DAILY LIMIT. KILLING.")
            await plug.async_turn_off()
            update_disk_row(
                last_row['Session_ID'], 
                End_Time=datetime.now().strftime("%H:%M:%S"),
                Status="DAILY_LIMIT_STOP",
                Actual_Min=round(elapsed/60, 2),
                Actual_Hours=round(elapsed/3600, 4),
                Notes="Crashed & Hit Daily Cap"
            )
            return "COOLDOWN", time.time(), 0, 0

        # Normal Overtime
        if elapsed > target_sec:
            print(f"🚨 SESSION OVERTIME. KILLING.")
            await plug.async_turn_off()
            update_disk_row(
                last_row['Session_ID'], 
                End_Time=datetime.now().strftime("%H:%M:%S"),
                Status="CRASHED_OVERTIME",
                Actual_Min=round(elapsed/60, 2),
                Actual_Hours=round(elapsed/3600, 4),
                Notes="Crashed & Exceeded Target"
            )
            return "COOLDOWN", time.time(), 0, 0
        
        else:
            print(f"✅ RESUMING SESSION. Time remaining within limits.")
            await plug.async_turn_on()
            return "RUNNING", start_ts, target_sec, int(last_row['Session_ID'])

    # 2. COOLDOWN CHECK
    if last_row.get('End_Time') != "..." and last_row.get('End_Time'):
        try:
            et_obj = datetime.strptime(last_row['End_Time'], "%H:%M:%S")
            end_ts = datetime.now().replace(hour=et_obj.hour, minute=et_obj.minute, second=et_obj.second).timestamp()
            if (time.time() - end_ts) < COOLDOWN_DURATION:
                return "COOLDOWN", end_ts, 0, 0
        except: pass

    return "IDLE", 0, 0, 0

async def worker(plug):
    global emergency_ram_backup
    print("🤖 ENGINE ONLINE")
    
    ensure_file_integrity()
    write_system_note("SYSTEM_BOOT", "Program Started")
    current_mode, mode_start_ts, current_target, current_sid = await startup_check(plug)
    last_heartbeat = 0
    
    print(f"🧠 MODE: {current_mode}")

    while True:
        try:
            # MIDNIGHT KILL
            now_dt = datetime.now()
            if now_dt.hour == 23 and now_dt.minute == 59 and now_dt.second >= 58:
                print("\n🕛 MIDNIGHT.")
                await plug.async_turn_off()
                if current_mode == "RUNNING":
                    update_disk_row(current_sid, Status="MIDNIGHT_STOP", End_Time="23:59:59")
                sys.exit()

            humidity = await data_queue.get()
            now = time.time()
            daily_total, primary_done, _ = get_brain_decision_data()

            # ==================
            # STATE: RUNNING
            # ==================
            if current_mode == "RUNNING":
                elapsed = now - mode_start_ts
                
                # HEARTBEAT
                if now - last_heartbeat > 30:
                    update_disk_row(
                        current_sid, 
                        Actual_Min=round(elapsed/60, 2),
                        Actual_Hours=round(elapsed/3600, 4)
                    )
                    last_heartbeat = now
                
                sys.stdout.write(f"\r⏳ RUNNING: {elapsed/60:.1f}m / {current_target/60:.0f}m | Hum: {humidity}%   ")
                sys.stdout.flush()

                # STOP: Target Hit OR Daily Limit Hit
                if elapsed >= current_target or (daily_total + elapsed) >= MAX_DAILY_TOTAL:
                    stop_status = "COMPLETED"
                    stop_note = "Target Reached"
                    
                    if (daily_total + elapsed) >= MAX_DAILY_TOTAL:
                        print(f"\n🛑 DAILY LIMIT HIT. HARD STOP.")
                        stop_status = "DAILY_LIMIT_STOP"
                        stop_note = "Max Daily Cap Reached"
                    else:
                        print(f"\n🛑 TARGET REACHED.")
                    
                    update_disk_row(
                        current_sid,
                        End_Time=datetime.now().strftime("%H:%M:%S"),
                        Status=stop_status,
                        End_Hum=humidity,
                        Actual_Min=round(elapsed/60, 2),
                        Actual_Hours=round(elapsed/3600, 4),
                        Daily_Cumulative_Hours=round((daily_total + elapsed)/3600, 4),
                        Notes=stop_note
                    )
                    
                    await plug.async_turn_off()
                    current_mode = "COOLDOWN"
                    mode_start_ts = now
                    emergency_ram_backup = {}

            # ==================
            # STATE: COOLDOWN
            # ==================
            elif current_mode == "COOLDOWN":
                ensure_file_integrity()
                elapsed = now - mode_start_ts
                if elapsed < COOLDOWN_DURATION:
                    sys.stdout.write(f"\r❄️ COOLDOWN: {(COOLDOWN_DURATION - elapsed)/60:.1f}m left   ")
                    sys.stdout.flush()
                else:
                    print("\n✅ COOLDOWN DONE.")
                    current_mode = "IDLE"

            # ==================
            # STATE: IDLE
            # ==================
            elif current_mode == "IDLE":
                if daily_total >= MAX_DAILY_TOTAL:
                    sys.stdout.write(f"\r🛑 LIMIT: {daily_total/3600:.2f}h used. Sleep.   ")
                    sys.stdout.flush()
                else:
                    sys.stdout.write(f"\r👀 IDLE: {humidity}% | Primary Done: {primary_done}   ")
                    sys.stdout.flush()
                    
                    base_target = 0
                    evt = ""
                    
                    if not primary_done and humidity >= PRIMARY_THRESHOLD:
                        base_target = PRIMARY_DURATION
                        evt = "PRIMARY_RUN"
                    elif humidity >= SECONDARY_THRESHOLD:
                        base_target = SECONDARY_DURATION
                        evt = "SECONDARY_RUN"
                    
                    if evt:
                        # --- ⚡ DYNAMIC CAPPING LOGIC ---
                        # 1. Calculate Budget Remaining
                        budget_remaining = MAX_DAILY_TOTAL - daily_total
                        
                        # 2. Cap the target
                        final_target = min(base_target, budget_remaining)
                        is_capped = final_target < base_target
                        
                        if final_target <= 60: # If less than 1 min left, don't bother
                            print("\n⚠️ Not enough daily budget to start.")
                            continue

                        print(f"\n⚡ TRIGGER: {evt}")
                        if is_capped:
                            print(f"⚠️ TARGET CAPPED: {base_target/60:.0f}m -> {final_target/60:.0f}m (Budget Limit)")

                        # 3. Write & Start
                        current_sid = write_new_run_to_disk(evt, humidity, final_target, daily_total, is_capped)
                        await plug.async_turn_on()
                        
                        current_mode = "RUNNING"
                        mode_start_ts = now
                        current_target = final_target

        except Exception as e:
            print(f"❌ ERROR: {e}")
        finally:
            data_queue.task_done()

async def main():
    print(f"🚀 MoldGuard-AI v17.0: HARD CAP ENFORCER")
    
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