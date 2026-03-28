import time

def main():
    print("Worker started...", flush=True)
    while True:
        print("Polling for jobs...", flush=True)
        time.sleep(5)

if __name__ == "__main__":
    main()
