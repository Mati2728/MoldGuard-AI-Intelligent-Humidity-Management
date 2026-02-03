# 🛡️ MoldGuard-AI  
### Autonomous, Compressor-Safe Humidity Control System (Edge-Based)

MoldGuard-AI is a **local, autonomous humidity management system** built to solve a *real and persistent indoor mold problem* using **engineering-grade control logic**.

It combines Bluetooth sensors, Wi-Fi power control, and a time-aware state machine to **remove moisture efficiently**, **reduce electricity usage**, and **protect both people and hardware**.

---

## 📖 The Story (Why This Exists)

I live in **Koblenz, Germany**, where indoor humidity in my room stayed consistently between **70–80% RH**.

The consequences were serious:
- Mold growth every **1–2 weeks**
- Constant cleaning
- Breathing discomfort
- Real health concerns, especially for **children and elderly people**, who are more vulnerable to **mold- and humidity-related lung problems**

A dehumidifier alone did not solve the problem — **how it was controlled mattered more than the machine itself**.

---

## ❌ Why Existing Solutions Failed

1. **Ecosystem Lock-In**  
   - Sensors and smart plugs could not communicate directly  
   - Vendors required a **paid proprietary hub (€30+)**

2. **Naive Automation**  
   - Simple timers ignore real humidity
   - Built-in apps toggle ON/OFF frequently
   - This wastes electricity and **damages compressors**

3. **No Physical Awareness**  
   - Moisture is stored in **walls, furniture, fabrics**
   - Short runs dry air but **do not stop mold**
   - Continuous operation is inefficient and unsafe

---

## 💡 What MoldGuard-AI Does

MoldGuard-AI turns a Mac Mini into an **edge-computing control system** that:

- Reads humidity via **Bluetooth (BLE)**
- Controls power via **Wi-Fi**
- Applies **time-based extraction logic**
- Enforces mandatory rest periods
- Logs every decision for transparency and recovery

The result:
- **Lower average electricity usage**
- **Higher moisture removal efficiency**
- **Stable, healthy indoor air**

---

## 🧠 Core Control Philosophy

> **Humidity must be controlled with time and patience — not constant switching.**

Key insight:
- Moisture leaves walls and furniture **slowly**
- Cooldown periods allow stored moisture to **re-enter the air**
- Each new run starts at a higher condensation potential
- This makes the dehumidifier **more effective while running less**

---

## 🔁 Control Logic (State Machine)

The system operates as a **deterministic temporal state machine**:

- `IDLE` → monitoring humidity
- `RUNNING` → dehumidifier ON
- `COOLDOWN` → mandatory rest & moisture release phase

State transitions depend on **humidity and elapsed time**, not momentary sensor noise.

---

## 📏 Humidity Thresholds

| Purpose | Relative Humidity |
|------|------------------|
| Primary trigger (deep drying) | ≥ 65% |
| Secondary trigger (maintenance) | ≥ 57% |

---

## ⏱ Run Strategy (Engineering Logic)

### 1️⃣ Primary Run — Deep Extraction
- **Trigger:** RH ≥ 65%
- **Duration:** **5 hours**
- **Purpose:**
  - Remove moisture from **walls, furniture, fabrics**
  - Stop mold growth at the structural level

---

### 2️⃣ Secondary Run — Maintenance
- **Trigger:** RH ≥ 57%
- **Duration:** **1.5 hours**
- **Purpose:**
  - Prevent rebound humidity
  - Maintain a safe equilibrium

---

### 3️⃣ Mandatory Cooldown — Efficiency & Safety Phase
- **Duration:** **2.5 hours**
- **Purpose:**
  - Protect the compressor (pressure equalization, thermal rest)
  - Allow walls and furniture to **release stored moisture**
  - Increase efficiency of the next run
  - Reduce unnecessary electricity consumption

Cooldown time is **productive**, not wasted.

---

### 4️⃣ Daily Safety Cap
- **Maximum runtime:** **7 hours/day**
- Prevents overuse
- Reduces energy cost
- Extends hardware lifespan

---

## 🛑 Compressor Protection

The system explicitly prevents:
- Short cycling
- Rapid restarts
- Restart under pressure
- Continuous 24/7 operation

All OFF periods exceed compressor equalization requirements by a wide margin.

---

## 📊 Observability & Reliability

Each day produces a **CSV log** containing:

- Session ID
- Start / end timestamps
- Event type
- Start & end humidity
- Target vs actual runtime
- Daily cumulative runtime
- Crash or recovery notes

### Reliability Features
- Atomic file writes
- Header validation
- Temporary file replacement
- RAM-backed emergency recovery
- Automatic session repair after reboot

---

## 🧪 Real-World Results

### Before MoldGuard-AI
- Manual or continuous operation
- **~18 hours** required to extract **~2.5 liters**
- High electricity usage
- Poor long-term mold control

### With MoldGuard-AI
- Time-aware extraction + enforced rest
- Same **~2.5 liters extracted in ~7–8 hours**
- Fewer operating hours
- Lower electricity consumption
- Stable, healthier indoor air

---

## 🧰 Hardware Used

- **Hygrometer:**  
  SwitchBot Meter (Bluetooth LE)  
  https://www.amazon.de/dp/B09QBR7XJD

- **Smart Plug:**  
  Meross MSS305  
  https://www.amazon.de/dp/B0DCVQC3RJ

- **Dehumidifier:**  
  Comfee 16L Compressor Dehumidifier  
  https://www.amazon.de/dp/B0D7YP21YT

- **Controller:**  
  Apple Mac Mini M4

---

## 💻 Software Stack

- Python 3.14
- `bleak` (Bluetooth LE)
- `meross-iot` (Wi-Fi control)
- Async, non-blocking event loop
- macOS (edge execution)

⚠️ This project is licensed for **non-commercial use only**. Commercial or business use is strictly prohibited.

---

## 👤 Author

**Ganesh Babu**  
University of Koblenz  

🌐 https://ganeshbabu.in
