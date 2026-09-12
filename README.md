# 🍱 TiffinManager

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![CLI Framework](https://img.shields.io/badge/CLI-Typer%20%2B%20Rich-emerald.svg)](https://typer.tiangolo.com/)
[![Dockerized](https://img.shields.io/badge/Docker-Compose-cyan.svg)](https://www.docker.com/)
[![CI/CD](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-purple.svg)](https://github.com/features/actions)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**TiffinManager** is a high-performance personal meal tracking CLI and web transparency dashboard designed for room-sharing flatmates, hostels, and tiffin meal tracking.

It combines an interactive terminal interface, itemized billing analytics, automated cloud/database sync, and a responsive web dashboard with **Privacy Key Protection** and **Light/Dark theme toggles**.

---

## ✨ Key Features

- 🍱 **Smart Interactive Recording (`tiffin record`)**: Log lunch and dinner attendance with smart defaults based on historical meal habits.
- 📅 **Daily Attendance History Matrix (`tiffin history`)**: View a date-by-date matrix showing day/night slots, ate vs. didn't eat status, and regular vs. special tiffins per person.
- 🔒 **Privacy-Protected Live Web Dashboard (`tiffin serve`)**:
  - **Public View**: Displays date-wise meal totals (e.g. *3 Tiffins Taken*) to preserve personal privacy.
  - **Itemized Secret Key Unlock**: Flatmates can enter a secret key to unlock individual person breakdowns and itemized dues.
  - **Light / Dark Mode**: Glassmorphism design with `Plus Jakarta Sans` typography and smooth theme toggling.
- 🔄 **Real-Time Auto-Sync & Cloud Backups**:
  - Automatically creates rolling local database backups on every write operation.
  - Auto-syncs database changes to live server over HTTPS when `.env` is configured.
- 💰 **Billing & Dues Management (`tiffin settle` / `tiffin bill`)**: Itemized invoice breakdown, partial settlement logging, net dues calculation, and WhatsApp summary generator.
- 🐳 **Dockerized 1-Click VPS Deployment**: Production-ready `Dockerfile`, `docker-compose.yml`, Nginx reverse proxy generator, and GitHub Actions CI/CD pipeline.

---

## 🚀 Quick Start

### 1. Local Installation

```bash
# Clone the repository
git clone https://github.com/Parikaragarwal/TiffinManager.git
cd TiffinManager

# Create virtual environment & install CLI
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Initialize database
tiffin init
```

### 2. Daily CLI Usage

```bash
# Record today's lunch or dinner
tiffin record

# View today's status
tiffin today

# View daily attendance history matrix across flatmates
tiffin history

# View billing summary and pending dues
tiffin bill

# Record a payment settlement
tiffin settle
```

---

## 🌐 Live Web Dashboard & Deployment

### Run Live Web Server

```bash
# Start live server locally or on VPS (default port: 8765)
tiffin serve --port 8765

# Run in background daemon mode
tiffin serve --port 8765 --bg

# Generate Nginx reverse proxy configuration
tiffin serve --nginx --domain tiffin.parikar.in
```

### Deploy with Docker Compose

```bash
# 1. Copy environment variables
cp .env.example .env
nano .env   # Set TIFFIN_SYNC_KEY=your_secret_passphrase

# 2. Build and launch container
docker compose up -d --build
```

---

## 📖 CLI Command Reference

| Command | Usage | Description |
|---|---|---|
| `record` | `tiffin record` | Interactively record lunch/dinner attendance for flatmates. |
| `today` | `tiffin today` | Quick shortcut to inspect or record today's meal status. |
| `history` | `tiffin history` | View daily attendance & meal type matrix for each person. |
| `status` | `tiffin status` | Inspect single date attendance table and cost breakdown. |
| `settle` | `tiffin settle` | Record payment transactions and clear pending dues. |
| `bill` | `tiffin bill` | View overall billing statement or itemized person invoice. |
| `report` | `tiffin report` | Detailed 6-section analytics consumption report. |
| `missing` | `tiffin missing` | Audit unrecorded/missing meal dates in the current month. |
| `sync` | `tiffin sync` | Push local database changes to live server. |
| `export` | `tiffin export` | Export report to CSV, HTML dashboard, or WhatsApp text format. |
| `serve` | `tiffin serve` | Run live transparent web dashboard server. |
| `backup` | `tiffin backup` | Create timestamped local and cloud database backup. |
| `restore` | `tiffin restore` | Restore database state from local file or JSON dump. |

---

## 🛠️ Architecture & Tech Stack

- **CLI Layer**: Python 3.10+, [Typer](https://typer.tiangolo.com/), [Rich](https://rich.readthedocs.io/)
- **Database Layer**: SQLite 3 with online SQLite backups and JSON serialization
- **Web Dashboard**: Vanilla JavaScript (ES6+), Glassmorphism CSS, Light/Dark mode, responsive grid layout
- **DevOps**: Docker, Docker Compose, Nginx, GitHub Actions CI/CD

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
