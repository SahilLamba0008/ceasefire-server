import time

def main():
    print("Worker started...")
    while True:
        print("Polling queue...")
        time.sleep(5)

if __name__ == "__main__":
    main()