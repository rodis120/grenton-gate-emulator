import os
import threading

import lupa.lua53 as lupa

from .cipher import CluCipher
from .client_manager import ClientManager
from .config import Config
from .objects.gate_object import GateObject
from .objects.grenton_object import GrentonObject
from .objects.objects import OBJECT_CLASS_DICT
from .types import RequestContext
from .utils import fetch_feature_values, parse_features_list


class CluLuaEngine:
    
    clu: GrentonObject

    def __init__(self, config: Config, client_manager: ClientManager, cipher: CluCipher, config_dir: str = "config") -> None:
        self.config = config
        self.client_manager = client_manager
        self.cipher = cipher
        self.config_dir = config_dir
        
        self.request_lock = threading.Lock()
        self.lua: lupa.LuaRuntime = None
        self.initialized = False
        
        self.req_context = RequestContext(None, None, None, None, None)
        
        self.reload()
       
    def execute(self, request_context: RequestContext, string: str):
        res = "nil"
        with self.request_lock:
            self.req_context = request_context
            res = self.lua.eval(f"tostring({string})")
        return res

    def reload(self):
        self.initialized = False
        self.lua = lupa.LuaRuntime()
        
        globals = self.lua.globals()
        globals["checkAlive"] = self._check_alive
        globals["OBJECT"] = {"new": self._new_object}
        globals["GATE"] = {"new": self._new_gate}
        globals["SYSTEM"] = {
            "Init": self._system_init,
            "fetchValues": self._fetch_values,
            "clientRegister": self._register_client,
            "clientDestroy": self._destroy_client,
            "mqttRegister": self._register_mqtt,
            "mqttDestroy": self._destroy_mqtt
        }

        with open(os.path.join(self.config_dir, "user.lua"), "r") as file:
            self.lua.execute(file.read())

        with open(os.path.join(self.config_dir, "om.lua"), "r") as file:
            self.lua.execute(file.read())
            
        self.clu.features[1].add_value_change_handler(self.client_manager.set_client_report_interval)
            
        self.lua.execute("SYSTEM.Init()")
        self.initialized = True
       
    def _system_init(self):
        self.clu.fire_event(0)
    
    def _new_object(self, _, obj_class, *args) -> GrentonObject:
        obj = OBJECT_CLASS_DICT.get(obj_class, None)
        if obj:
            return obj(self, args)
        
        return GrentonObject(self, args) # return dummy object

    def _new_gate(self, _, *args) -> GrentonObject:
        if len(args) == 2:
            obj_class = args[0]
            return self._new_object(None, obj_class, args[1:])

        return GateObject(self, ())
    
    def _check_alive(self):
        return hex(self.config.serial_number)[2:]
    
    def _fetch_values(self, _, features) -> str:
        values = parse_features_list(features)
        
        return f"values:{fetch_feature_values(values)}"
    
    def _register_client(self, _, ip, port, client_id, features) -> str:
        values = parse_features_list(features)
        
        self.client_manager.register_client(ip, port, client_id, self.req_context.session_id, values)
        return f"clientReport:{client_id}:{fetch_feature_values(values)}"
    
    def _destroy_client(self, _, ip, port, client_id) -> str:
        self.client_manager.destroy_client(ip, port, client_id)
        return client_id
    
    def _register_mqtt(self, _, client_id, features) -> str:
        values = parse_features_list(features)
        
        self.client_manager.register_mqtt(client_id, self.req_context.session_id, values)
        return f"clientReport:1:{fetch_feature_values(values)}"
    
    def _destroy_mqtt(self, _, client_id) -> str:
        self.client_manager.destroy_mqtt(client_id)
        return client_id