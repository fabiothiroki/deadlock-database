import requests
import concurrent.futures
import random
import sys

# --- CONFIGURATION ---
# Since we run this INSIDE the container via 'exec', localhost refers to the container itself.
API_URL = "http://localhost:8000"
CONCURRENT_USERS = 8
TOTAL_REQUESTS = 20

def get_endpoint():
    """Determines safe vs unsafe based on CLI arguments"""
    if len(sys.argv) > 1 and sys.argv[1] == "safe":
        return "/transfer/safe"
    return "/transfer/unsafe"

def send_transfer(i, endpoint):
    # Randomize direction
    if random.choice([True, False]):
        payload = {"from_account": 1, "to_account": 2, "amount": 10}
        label = "Alice -> Bob"
    else:
        payload = {"from_account": 2, "to_account": 1, "amount": 10}
        label = "Bob -> Alice"

    try:
        resp = requests.post(f"{API_URL}{endpoint}", json=payload)
        if resp.status_code == 200:
            print(f"[{i}] ✅ Success: {label}")
            return "ok"
        elif resp.status_code == 500:
            print(f"[{i}] ❌ DEADLOCK: {label}")
            return "deadlock"
        else:
            print(f"[{i}] ⚠️ Error: {resp.status_code}")
            return "error"
    except Exception as e:
        print(f"Connection Error: {e}")
        return "error"

def main():
    endpoint = get_endpoint()
    mode_name = "SAFE (Fixed)" if "safe" in endpoint else "UNSAFE (Deadlock prone)"
    
    print(f"\n--- Starting Attack ---")
    print(f"Mode: {mode_name}")
    print(f"Target: {API_URL}{endpoint}")
    print(f"Users: {CONCURRENT_USERS}")
    
    # Reset DB first so we start fresh
    try:
        requests.post(f"{API_URL}/reset")
        print("Database reset successfully.\n")
    except Exception:
        print("❌ Error: Could not connect to API. Is the docker container running?")
        return

    # Run concurrent requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONCURRENT_USERS) as executor:
        # We use lambda to pass the specific endpoint to the worker function
        futures = [executor.submit(send_transfer, i, endpoint) for i in range(TOTAL_REQUESTS)]
        results = [f.result() for f in futures]

    print("\n--- Summary ---")
    print(f"Success:   {results.count('ok')}")
    print(f"Deadlocks: {results.count('deadlock')}")

if __name__ == "__main__":
    main()