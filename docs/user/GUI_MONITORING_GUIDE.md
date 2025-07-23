# 🖥️ Archivist GUI Monitoring Guide

## 🚀 Quick Access URLs

| Interface           | URL                        | Description                                 |
|---------------------|----------------------------|---------------------------------------------|
| Admin UI            | http://localhost:8080      | Main admin interface, queue management      |
| Monitoring Dashboard| http://localhost:5051      | Real-time system health, task analytics     |

**Note:**  
All legacy dashboards and web interfaces (including port 5000) are deprecated. Use only the above URLs for monitoring and control.

## Features

- **Admin UI (8080):**
  - Queue status and management
  - Celery worker status
  - City configuration
  - Task triggers
  - Embeds the Monitoring Dashboard

- **Monitoring Dashboard (5051):**
  - Real-time system health (CPU, memory, disk, Redis, Celery)
  - Task queue analytics and filtering
  - Performance metrics and charts
  - Live task progress and history

## How to Monitor

1. **Open the Monitoring Dashboard:**  
   [http://localhost:5051](http://localhost:5051)

2. **Open the Admin UI:**  
   [http://localhost:8080](http://localhost:8080)

3. **Do not use** any other ports or legacy dashboards.

---

## 🛑 Deprecated GUIs

- All GUIs on port 5000 and legacy dashboards are deprecated.
- All features are being consolidated into the above interfaces.

--- 