
import base64
import json
import os
from typing import Any

from .config import Config
from .module_manager import ModuleManager, Module
from .utils import padd_string

class ConfigManager:

    def __init__(self, config: Config, config_dir, module_manager: ModuleManager) -> None:
        self.config = config
        self.config_dir = config_dir
        self.module_manager = module_manager

        self.generate_config_files()

    def generate_config_files(self) -> None:
        modules = self.module_manager.modules.values()
        self._generate_config_json(modules)
        self._generate_config_txt(modules)

    def _generate_config_txt(self, modules) -> None:
        lines = ["00000000"]
        lines.append(padd_string(hex(self.config.serial_number)[2:]))
        lines.append(self.config.mac)
        lines.append(padd_string(hex(self.config.fw_type)[2:]))
        lines.append(padd_string(hex(self.config.fw_api_ver)[2:]))
        lines.append(padd_string(hex(self.config.hw_type)[2:]))
        lines.append(padd_string(hex(self.config.hw_ver)[2:]))
        
        for line in {self._module_to_txt(mod) for mod in modules}:
            lines.append(line)

        with open(os.path.join(self.config_dir, "config.txt"), "w+") as f:
            f.writelines([line + "\n" for line in lines])

    def _module_to_txt(self, module: Module):
        info = module.module_info
        sn = padd_string(hex(info.serial_number)[2:])
        hw_type = padd_string(hex(info.hw_type)[2:], 2)
        fw_type = padd_string(hex(info.fw_type)[2:], 2)
        api_ver = padd_string(hex(info.fw_api_ver)[2:], 2)

        return f"{sn}:{hw_type}:{fw_type}:{api_ver}"

    def _generate_config_json(self, modules) -> None:
        data = {}
        data["sn"] = self.config.serial_number
        data["mac"] = self.config.mac
        data["hwType"] = self.config.fw_type
        data["hwVer"] = self.config.hw_ver
        data["fwType"] = self.config.fw_type
        data["fwVer"] = self.config.fw_ver
        data["fwApiVer"] = self.config.fw_api_ver
        data["status"] = "OK"
        data["tfbusDevices"] = [self._module_to_json(mod) for mod in modules]
        data["zwaveDevices"] = []

        with open(os.path.join(self.config_dir, "config.json"), "w+") as f:
            json.dump(data, f)

    def _module_to_json(self, module: Module) -> dict[str, Any]:
        info = module.module_info
        data = {}
        data["sn"] = info.serial_number
        data["hwType"] = info.fw_type
        data["hwVer"] = info.hw_ver
        data["fwType"] = info.fw_type
        data["fwVer"] = info.fw_ver
        data["fwApiVer"] = info.fw_api_ver
        data["status"] = "OK"

        return data

    def load_project_key(self) -> tuple[bytes, bytes]:
        try:
            with open(os.path.join(self.config_dir, "project_key.txt"), "r") as f:
                key = base64.b64decode(f.readline())
                iv = base64.b64decode(f.readline())
                
                if len(key) != 16 or len(iv) != 16:
                    return bytes(16), bytes(16)
                
                return key, iv
        except:
            return bytes(16), bytes(16)
        
    def save_project_key(self, key: bytes, iv: bytes) -> None:
        
        try:
            with open(os.path.join(self.config_dir, "project_key.txt"), "wb+") as f:
                f.write(base64.b64encode(key) + b"\r\n")
                f.write(base64.b64encode(iv) + b"\r\n")
        except:
            pass
