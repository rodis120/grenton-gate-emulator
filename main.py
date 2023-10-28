
from clu_emulator.clu_emulator import CluEmulator

if __name__ == "__main__":
    emulator = CluEmulator("conf.json")
    emulator.start()
    print("Emulator started")
    
    import time
    while True:
        time.sleep(10)