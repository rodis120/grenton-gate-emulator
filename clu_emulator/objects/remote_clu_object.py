
from typing import Any

from ..clu_client import CluClient
from ..utils import int_to_ip
from .grenton_object import GrentonObject


class RemoteCluObject(GrentonObject):
    
    def __init__(self, engine, args) -> None:
        super().__init__(engine, args)
        
        self.ip = int_to_ip(args[0])
        self.clu_client = CluClient(self.ip, self.engine.cipher, timeout=0.2)
        
        self.methods[0] = self._send_request
        
    def _send_request(self, payload: str) -> Any:
        return self.clu_client.send_lua_request(payload)