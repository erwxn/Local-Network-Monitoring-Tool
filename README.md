# 📡 LocalNet Monitor CLI

![Python](https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)

## 📋 Overview

**LocalNet Monitor** is a lightweight, terminal-based network monitoring tool written in Python. It provides real-time visibility into the availability and performance of network hosts. 

Designed for network administrators and enthusiasts, it utilizes **ICMP Echo Requests** (Ping) to track latency, calculate jitter, and monitor packet success rates across multiple targets simultaneously using multi-threading. The results are rendered in a beautiful, live-updating dashboard using the `rich` library.

## ✨ Key Features

* **⚡ Real-Time Dashboard:** Live-updating table displaying status, latency, and trends.
* **🧵 Multi-Threaded:** Uses `ThreadPoolExecutor` to monitor multiple hosts concurrently without UI blocking.
* **📊 Advanced Metrics:** * **Jitter:** Calculates network stability (latency variation).
    * **Trend Indicators:** Visual cues (`↑` / `↓`) for latency spikes or drops.
    * **Success Rate:** Tracks packet loss percentage over time.
* **🔍 Smart Host Parsing:**
    * Standard IPs (e.g., `8.8.8.8`)
    * **CIDR Notation** (e.g., `192.168.1.0/24`)
    * **IP Ranges** (e.g., `192.168.1.10-192.168.1.50`)
    * **URLs** (e.g., `https://www.youtube.com/watch?v=xvFZjo5PgG0&list=RDxvFZjo5PgG0&start_radio=1`)
* **🏷️ Auto-Resolution:** Automatically resolves IP addresses to hostnames.

## 🛠️ Tech Stack

* **Language:** Python 3
* **UI/TUI:** [Rich](https://github.com/Textualize/rich)
* **Networking:** [ping3](https://github.com/kyan001/ping3), `ipaddress`, `socket`
* **Concurrency:** `threading`, `concurrent.futures`

## 🚀 Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/localnet-monitor.git](https://github.com/YOUR_USERNAME/localnet-monitor.git)
    cd localnet-monitor
    ```

2.  **Install dependencies:**
    ```bash
    pip install rich ping3
    ```

## ⚙️ Configuration

Create a `hosts.txt` file in the root directory to define your targets. You can mix and match formats:

```text
# Single IP
8.8.8.8

# Domain Name
google.com

# CIDR Subnet (Scans the whole subnet)
192.168.1.0/24

# IP Range
10.0.0.50-10.0.0.60
