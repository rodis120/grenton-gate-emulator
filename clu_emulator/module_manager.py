
import asyncio
from dataclasses import dataclass
from typing import Any

from pyvlx import OpeningDevice, PyVLX
from .config import Config


@dataclass
class ModuleInfo:
    serial_number: int
    hw_type: int
    hw_ver: int
    fw_type: int
    fw_api_ver: int
    fw_ver: str

class Module:

    def __init__(self, module_info: ModuleInfo) -> None:
        self.module_info = module_info
        self.objects: dict[int, list[Any]] = {}

    def get_object(self, obj_class: int, index: int):
        objects = self.objects.get(obj_class)
        if objects and len(objects) > index:
            return objects[index]

        return None

class VeluxOpeningDeviceModule(Module):
    
    def __init__(self, device: OpeningDevice) -> None:
        super().__init__(ModuleInfo(device.serial_number, 23, 1, 2, 2, "02"))

        self.objects[12] = [0]
        self.objects[24] = [device]

class ModuleManager:

    def __init__(self, config: Config) -> None:
        self.modules: dict[int, Module] = {}

        self.pyvlx = PyVLX(host=config.velux_ip, password=config.velux_password)

    def reload_modules(self) -> None:
        asyncio.get_event_loop().run_until_complete(self.pyvlx.load_nodes())
        self.modules.clear()

        for node in self.pyvlx.nodes:
            if isinstance(node, OpeningDevice):
                self.add_module(VeluxOpeningDeviceModule(node))

    def get_module_by_sn(self, serial_number: int) -> Module | None:
        return self.modules.get(serial_number)

    def add_module(self, module: Module) -> None:
        self.modules[module.module_info.serial_number] = module
    