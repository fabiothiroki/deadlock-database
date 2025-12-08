# Database Deadlock Demo: Bank Transfer 🏦💥

This project is a practical demonstration of **Database Deadlocks**, created to support [my article](https://medium.com/p/72bea0d18537). 

It simulates a high-concurrency banking environment where multiple users try to transfer money to each other simultaneously. It demonstrates how a naive implementation causes the database to crash (deadlock) and how a simple engineering pattern (Lock Ordering) fixes it completely.

**Tech Stack:**
*   **Language:** Python 3.14 (FastAPI)
*   **Database:** PostgreSQL 18
*   **Driver:** Psycopg3 (Raw SQL, no ORMs)
*   **Infrastructure:** Docker & Docker Compose

---

## 📋 Prerequisites

To keep your local machine clean, this entire project runs inside Docker. You do not need to install Python or PostgreSQL locally.

You only need **Docker** installed:

*   **Windows / Mac:** Install [Docker Desktop](https://www.docker.com/products/docker-desktop).
*   **Linux:** Install [Docker Engine](https://docs.docker.com/engine/install/) and [Docker Compose](https://docs.docker.com/compose/install/).

Check if it is installed by running:
```bash
docker --version
docker compose version
```

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/deadlock-demo.git
cd deadlock-demo
```

### 2. Start the Environment

This command will build the Python application and start the database.

```bash    
docker compose up --build
```

### 3. Run the Simulation

Open a new terminal window (keep the server running in the first one). We will run the attack script inside the container.

#### Scenario 1: The Crash (Unsafe Mode) ❌
This demonstrates the deadlock.

```bash
docker compose exec app python attack.py
```

#### Scenario 2: The Fix (Safe Mode) ✅
This demonstrates the fix using Lock Ordering.

```bash  
docker compose exec app python attack.py safe
```

### 4. Stop the App
When you are done, stop the containers:

```bash
docker compose down
```

  