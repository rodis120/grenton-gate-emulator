
import asyncio

from pyvlx import OpeningDevice, Position, Blind

from .feature import Feature
from .gate_object import GrentonObject

def _async_to_sync(awaitable):
    return asyncio.get_event_loop().run_until_complete(awaitable)

def _map_value(value, in_min, in_max, out_min, out_max):
    return (value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

class RollerShutterObject(GrentonObject):
    
    def __init__(self, engine, args) -> None:
        super().__init__(engine, args)

        self.features[0] = Feature(int, settable=False) # state
        self.features[3] = Feature(int, settable=False, initial_value=1) # up
        self.features[4] = Feature(int, settable=False, initial_value=0) # down
        self.features[7] = Feature(int, settable=False) # position
        self.features[8] = Feature(int, settable=False) # lamel position

        self.methods[0] = self.open
        self.methods[1] = self.close
        self.methods[2] = self.start
        self.methods[3] = self.stop
        self.methods[4] = self.hold
        self.methods[5] = self.hold_up
        self.methods[6] = self.hold_down
        self.methods[9] = self.set_lamel_position
        self.methods[10] = self.set_position

        module = args[0]
        index = args[1]
        self.device: OpeningDevice = module.get_object(24, index)
        self.device.register_device_updated_cb(self.update_callback)

        self.direction = True # True - up False - down
        self.last_direction = False

        self.update_position()
        
    def update_callback(self, device):
        self.update_position()

    def update_position(self):
        self.features[7].set_value(self.device.position.position_percent, True)
        if isinstance(self.device, Blind):
            value = _map_value(self.device.orientation.position_percent, 100, 0, 0, 90)
            self.features[8].set_value(value, True)

    def set_position(self, value):
        _async_to_sync(self.device.set_position(Position(position_percent=100 - value), wait_for_completion=False))

    def set_lamel_position(self, value):
        if isinstance(self.device, Blind):
            value = _map_value(value, 0, 90, 100, 0)
            _async_to_sync(self.device.set_orientation(Position(position_percent=value), wait_for_completion=False))

    def open(self, time):
        self.direction = True
        _async_to_sync(self.device.open(wait_for_completion=False))

    def close(self, time):
        self.direction = False
        _async_to_sync(self.device.close(wait_for_completion=False))

    def start(self, time):
        if not self.last_direction:
            self.open(time)
        else:
            self.close(time)

    def stop(self):
        _async_to_sync(self.device.stop(wait_for_completion=False))

    def hold(self):
        self.stop()
        self.last_direction = not self.direction

    def hold_up(self):
        self.stop()
        self.last_direction = False

    def hold_down(self):
        self.stop()
        self.last_direction = True