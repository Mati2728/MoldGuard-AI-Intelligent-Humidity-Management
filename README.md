# MoldGuard-AI: Intelligent Humidity Management 🛡️🏠

**MoldGuard-AI** is an autonomous climate-control system built to combat severe indoor humidity and mold growth. Developed as an edge-computing solution on a Mac Mini, this system bridges the gap between **SwitchBot** sensors and **Meross** smart plugs, enforcing industrial-grade logic to maintain a healthy living environment.

---

## 🛑 The Problem: My Situation
Living in Koblenz, I faced a recurring nightmare: **70% to 80% humidity levels** that were literally choking me off. Despite my best efforts, I was dealing with **mold growth every two weeks**, requiring constant cleaning and posing a serious health risk. 

I bought a dehumidifier and a sensor, but I immediately hit the **"Ecosystem Wall"**:
1. **The Hub Problem:** To make the sensor talk to the plug, the manufacturers want you to buy a €30+ proprietary Hub. As a Data Science student, I knew my Mac Mini had the hardware to do this for free, but no app existed to bridge them.
2. **"Dumb" Automation:** Basic timers don't react to real-time data. If I left the machine on, it wasted power; if I left it off, the mold returned.
3. **Hardware Stress:** Constantly toggling a dehumidifier on/off ruins the compressor. I needed a system with "memory" and "patience."



## 🚀 The Solution: Smart Logic Engine
I developed **MoldGuard-AI** to act as a local "Brain." It bypasses the need for a proprietary hub by using the Mac Mini's Bluetooth radio to "wake-lock" the sensor and its Wi-Fi to control the power.

The system enforces a **Temporal State Machine** to optimize air quality and machine life:
- **5-Hour Deep Extraction:** Once the threshold (50%) is hit, the machine runs for a mandatory 5-hour block. This is the only way to pull deep moisture out of walls and furniture to stop mold spores from germinating.
- **1.5-Hour Compressor Recovery:** To prevent hardware failure, the system enforces a 90-minute "hard-off" period after every run.
- **7-Hour Daily Cap:** A safety limit to manage electricity costs and prevent the machine from overheating.

## 🛠 Hardware Stack
- **Hygrometer:** [SwitchBot Meter](https://www.amazon.de/dp/B09QBR7XJD)
- **Power Actuator:** [Meross MSS305 Smart Plug](https://www.amazon.de/dp/B0D7YP21YT)
- **Dehumidifier:** [Comfee 16L](https://www.amazon.de/dp/B0DCVQC3RJ)

## 📊 Data & Analytics
As a Data Scientist, I need to see the proof. This system generates **Daily CSV Reports** (e.g., `humidity_stats_2026-01-31_Saturday.csv`) including:
- **Rolling 24-Hour Averages:** To track if the room is actually getting drier over time.
- **Hourly Telemetry:** Logging humidity, temperature, and cumulative machine runtime.



## 💻 Tech Stack
- **Language:** Python 3.14 (macOS)
- **Communication:** `Bleak` (BLE) & `Meross-Iot` (Wi-Fi/MQTT)
- **Architecture:** Asynchronous, non-blocking event loop.

---
**Developed by [Ganesh Babu](https://ganeshbabu.in)** *M.Sc. Web and Data Science Student | University of Koblenz*