# 🛡️ MoldGuard-AI  
### Autonomous, Compressor-Safe Humidity Control System (Edge-Based)

MoldGuard-AI is a **local, autonomous humidity management system** built to solve a *real, persistent mold problem* in a residential environment.

This project was developed out of necessity — not as a demo — and applies **engineering-grade control logic** to protect both **human health** and **mechanical hardware**.

---

## 📖 The Story (Why This Exists)

I live in **Koblenz, Germany**, where indoor humidity in my room stayed consistently between **70–80% RH**.

The result:
- Mold growth every **1–2 weeks**
- Constant cleaning
- Breathing discomfort
- A real health concern

I bought a **dehumidifier**, but quickly realized the bigger problem wasn’t the machine — it was **how it was controlled**.

### What went wrong with existing solutions

1. **Ecosystem Lock-In**
   - My humidity sensor and smart plug could not communicate
   - Vendors required a **paid proprietary hub (€30+)**
   - No cross-brand automation without cloud dependency

2. **“Dumb” Automation**
   - Simple timers ignore real humidity
   - Built-in apps toggle ON/OFF too frequently
   - This **destroys compressor-based dehumidifiers**

3. **No Mechanical Awareness**
   - Compressors need:
     - long run cycles
     - pressure equalization
     - enforced rest
   - Consumer automations don’t respect this

As a **Web & Data Science student**, I already had an always-on **Mac Mini**.  
So instead of buying another hub, I built my own **local control brain**.

---

## 💡 What MoldGuard-AI Does

MoldGuard-AI turns a Mac Mini into an **edge-computing controller** that:

- Reads real-time humidity via **Bluetooth (BLE)**
- Controls power via **Wi-Fi**
- Enforces **time-based logic**, not reactive toggles
- Logs every decision for observability and recovery

No cloud.  
No vendor lock-in.  
No short cycling.

---

## 🧠 Core Control Philosophy

> **Humidity must be controlled with time and memory — not switches.**

MoldGuard-AI treats the dehumidifier as a **mechanical system**, not a smart toy.

Key principles:
- Moisture is stored in **walls, furniture, fabrics**
- Short runs dry air but **do not stop mold**
- Compressors fail from **frequent restarts**
- Safety must be enforced by logic, not user discipline

---

## 🔁 Control Logic (State Machine)

The system operates as a **deterministic temporal state machine**:

### States
- `IDLE` → monitoring humidity
- `RUNNING` → dehumidifier powered ON
- `COOLDOWN` → mandatory compressor rest

State transitions are governed by **time + humidity**, not momentary readings.

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
- **Reason:**
  - Pulls moisture out of walls and furniture
  - Breaks mold growth cycles at the structural level

### 2️⃣ Secondary Run — Maintenance
- **Trigger:** RH ≥ 57%
- **Duration:** **1.5 hours**
- **Reason:**
  - Prevents rebound humidity
  - Maintains safe equilibrium

### 3️⃣ Mandatory Cooldown
- **Duration:** **2.5 hours**
- **Reason:**
  - Allows refrigerant pressure equalization
  - Prevents thermal stress and oil migration

### 4️⃣ Daily Safety Cap
- **Maximum runtime:** **7 hours/day**
- Any run is **dynamically capped** if the daily budget is close

---

## 🛑 Compressor Safety Guarantees

The system explicitly prevents:
- Short cycling
- Rapid restarts
- Continuous 24/7 operation
- Restart after abrupt power loss

All rest periods exceed compressor equalization requirements by a wide margin.

---

## 📊 Observability & Fault Tolerance

Every day generates a **CSV report** with:

- Session ID
- Start / end timestamps
- Event type (PRIMARY / SECONDARY)
- Start & end humidity
- Target vs actual runtime
- Daily cumulative runtime
- Crash or recovery notes

### Reliability Features
- Atomic file writes
- Header validation
- Temporary file replacement
- RAM-backed emergency recovery
- Automatic session repair after reboot or crash

---

## 🧪 Real-World Results

- Initial humidity: **~79% RH**
- First drying phase: **~2.5 liters extracted**
- Stabilized operation:
  - ~6–7 hours compressor runtime/day
  - High extraction efficiency per run
  - Gradual moisture decline over days

Fast tank fill indicates **efficient extraction**, not excessive cycling.

---

## 🧰 Hardware Used (Actual Devices)

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
  Apple Mac Mini (always-on, local edge node)

---

## 💻 Software Stack

- **Language:** Python 3.14
- **Bluetooth:** `bleak`
- **IoT Control:** `meross-iot`
- **Architecture:** Async, non-blocking event loop
- **Platform:** macOS (edge execution)

---

## 🎯 Why This Project Matters (Recruiter Note)

This project demonstrates:
- Real-world problem solving
- Systems thinking (software + hardware)
- Fault-tolerant design
- State machines & time-based control
- Edge computing without cloud dependency
- Respect for physical system constraints

This is **not a tutorial project** — it is a deployed system solving a real problem.

---

## 👤 Author

**Ganesh Babu**  
M.Sc. Web & Data Science  
University of Koblenz  

🌐 https://ganeshbabu.in
