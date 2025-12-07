import requests
import concurrent.futures
import random

# Configuration
API_URL = "http://localhost:8000"
CONCURRENT_USERS = 8  # How many requests running at the exact same time
TOTAL_REQUESTS = 50   # Total transfers to attempt

def send_transfer(transfer_id):
    """
    Sends a single transfer request.
    Randomly decides direction (Alice->Bob or Bob->Alice)
    """
    # 50% chance for Alice->Bob, 50% chance for Bob->Alice
    if random.choice([True, False]):
        payload = {"from_account": 1, "to_account": 2, "amount": 10}
        direction = "Alice -> Bob"
    else:
        payload = {"from_account": 2, "to_account": 1, "amount": 10}
        direction = "Bob -> Alice"

    try:
        # Change to /transfer/safe to test the fix
        response = requests.post(f"{API_URL}/transfer/unsafe", json=payload)
        
        if response.status_code == 200:
            print(f"[{transfer_id}] ✅ Success: {direction}")
            return "success"
        elif response.status_code == 500:
            print(f"[{transfer_id}] ❌ DEADLOCK: {direction}")
            return "deadlock"
        else:
            print(f"[{transfer_id}] ⚠️ Error: {response.text}")
            return "error"
            
    except Exception as e:
        print(f"Request failed: {e}")
        return "error"

def run_attack():
    print(f"--- Starting Attack: {TOTAL_REQUESTS} requests with {CONCURRENT_USERS} concurrent users ---")
    
    # First, reset the DB so we have a clean slate
    requests.post(f"{API_URL}/reset")
    
    # We use a ThreadPool to simulate multiple users acting at once
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        # Submit all tasks to the pool
        futures = [executor.submit(send_transfer, i) for i in range(TOTAL_REQUESTS)]
        
        # Wait for them to finish and collect results
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    print("\n--- Results ---")
    print(f"Successful Transfers: {results.count('success')}")
    print(f"Deadlocks Triggered:  {results.count('deadlock')}")

if __name__ == "__main__":
    run_attack()