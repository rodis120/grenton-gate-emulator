
import time
from threading import Thread

from .grenton_object import Feature, GrentonObject


class UptimeFeature(Feature):
    
    def __init__(self) -> None:
        super().__init__(int, True, False)
        
        self._start_timestamp = time.time()
        
        self._thread = Thread(target=self.update_time_loop, daemon=True)
        self._thread.start()
        
    def update_time_loop(self):
        while True:
            t = time.perf_counter()
            self.set_value(int(time.time() - self._start_timestamp))
            t = time.perf_counter() - t
            
            if t < 1:
                time.sleep(1 - t)

class UnixTimeFeature(Feature):

    def __init__(self) -> None:
        super().__init__(int, True, False, None)

        self.update_thread = Thread(target=self.update_time, daemon=True)
        self.update_thread.start()

    def update_time(self):
        while True:
            self.set_value(int(time.time()))
            time.sleep(1)

class GateObject(GrentonObject):
    
    def __init__(self, engine, args) -> None:
        super().__init__(engine, args)

        engine.clu = self
        
        self.features[0] = UptimeFeature() # uptime
        self.features[1] = Feature(bool)   # client report interval
        self.features[2] = Feature(str)    # primary DNS
        self.features[3] = Feature(str)    # secondary DNS

        self.features[15] = UnixTimeFeature()