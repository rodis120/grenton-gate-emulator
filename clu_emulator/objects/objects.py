
from .grenton_object import GrentonObject, ModuleObject
from .remote_clu_object import RemoteCluObject
from .timer_object import TimerObject
from .roller_shutter_object import RollerShutterObject

        
OBJECT_CLASS_DICT = {
    1: RemoteCluObject,
    2: ModuleObject,
    6: TimerObject,
    12: GrentonObject,
    24: RollerShutterObject
}