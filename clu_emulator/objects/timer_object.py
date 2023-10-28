
from threading import Timer

from .feature import Feature
from .grenton_object import GrentonObject


class TimerObject(GrentonObject):
    
    timer: Timer | None = None
    
    def __init__(self, engine, args) -> None:
        super().__init__(engine, args)
        
        self.features[0] = Feature(int)
        self.features[1] = Feature(int)
        self.features[2] = Feature(int, settable=False)

        self.features[2].set_value(0, True)
        
        self.methods[0] = self.start
        self.methods[1] = self.stop
        
    def start(self) -> None:
        if self.timer:
            self.timer.cancel()
        self.timer = Timer(self.features[0].get_value() / 1000, self.on_timer)
        self.features[2].set_value(1, True)
        self.timer.start()
        
        self.fire_event(1)
        
    def stop(self) -> None:
        if self.timer:
            self.timer.cancel()
        self.features[2].set_value(0, True)
        
        self.fire_event(2)
    
    def on_timer(self) -> None:
        self.features[2].set_value(0, True)
        self.fire_event(0)
        
        if self.get(1) == 1:
            self.start()