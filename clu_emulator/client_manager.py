
import socket
import threading
import time
from abc import ABC, abstractmethod
from typing import Any

from clu_emulator.objects.grenton_object import Feature

from .objects.grenton_object import Feature
from .cipher import CluCipher
from .clu_cloud import CloudCommunicator
from .utils import fetch_values

CLIENT_LIFE_TIME = 60

class Observable(ABC):
    
    def __init__(self) -> None:
        super().__init__()
        self.prev_val = self.value()
        self.clients = set()
        
    def add_client(self, client):
        self.clients.add(client)
        
    def remove_client(self, client):
        self.clients.remove(client)
    
    def update(self) -> bool:
        new_val = self.value()
        out = self.prev_val != new_val
        self.prev_val = new_val
        
        for client in self.clients:
            client.set_update_flag()
        
        return out

    @abstractmethod
    def value(self) -> Any:
        raise NotImplementedError
    
class ObservableFeature(Observable):
    
    def __init__(self, feature: Feature):
        self.feature = feature
        super().__init__()
    
    def value(self) -> Any:
        return self.feature.get_value()
    
class ObservableUserVariable(Observable):
    
    def __init__(self, lua, var_name: str) -> None:
        self.lua = lua
        self.name = var_name
        super().__init__()
    
    def value(self) -> Any:
        return self.lua.eval(self.name)
        
class Client:
    
    def __init__(
        self,
        client_id: int | str,
        session_id: int,
        observables: list[Observable]
    ) -> None:
        self.client_id = client_id
        self.session_id = session_id
        self.observables = observables
        self.update_flag = False
        self.registration_timestamp = time.time()
        
        for ob in observables:
            ob.add_client(self)
            
    def set_update_flag(self) -> None:
        self.update_flag = True

    def unlink_observables(self) -> None:
        for ob in self.observables:
            ob.remove_client(self)
            
class LocalClient(Client):
    
    def __init__(self, ip: str, port: int, client_id: int, session_id: int, observables: list[Observable]) -> None:
        super().__init__(client_id, session_id, observables)

        self.ip = ip
        self.port = port

class ClientManager:
    
    def __init__(self, cipher: CluCipher, cloud_comm: CloudCommunicator, hostip: str = "") -> None:
        self._cipher = cipher
        self._cloud = cloud_comm
        
        if hostip == "":
            self._hostip = socket.gethostbyname(socket.gethostname())
        else:
            self._hostip = hostip
        
        self._observables_f: dict[Feature, ObservableFeature] = {}
        self._observables_uv: dict[str, ObservableUserVariable] = {}
        self._observables: set[Observable] = set()
        
        self._clients_mqtt: dict[int, Client] = {}
        self._clients_local: dict[tuple[str, int, int], LocalClient] = {}
        self._clients_lock = threading.RLock()
        
        self._stop_event = threading.Event()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self._client_report_interval = 1.0

        self._manager_thread = threading.Thread(target=self._manager_loop, daemon=True)
        self._manager_thread.start()
        
    def close(self):
        self._stop_event.set()
        self._manager_thread.join()
        self._sock.close()
        
        self.clear()
        
    def set_client_report_interval(self, value):
        self._client_report_interval = value / 1000.0
    
    def register_client(self, lua, ip: str, port: int, client_id: int, session_id: int, observables: list[str | Feature]) -> None:
        if not (isinstance(ip, str) and isinstance(port, int) and isinstance(client_id, int)):
            return
        
        with self._clients_lock:
            
            obs = []
            for obj in observables:
                ob = self._observable_factory(lua, obj)
                self._observables.add(ob)
                obs.append(ob)
                
            client = LocalClient(ip, port, client_id, session_id, obs)
        
            key = (ip, port, client_id)
            if key in self._clients_local.keys():
                self._clients_local.pop(key).unlink_observables()
                
            self._clients_local[key] = client
        
    def destroy_client(self, ip: str, port: int, client_id: int) -> None:
        if not (isinstance(ip, str) and isinstance(port, int) and isinstance(client_id, int)):
            return
        
        with self._clients_lock:
            key = (ip, port, client_id)
            if key not in self._clients_local.keys():
                return
            
            self._clients_local.pop(key).unlink_observables()
            
    def register_mqtt(self, lua, client_id: str, session_id: int, observables: list[str | Feature]) -> None:
        if not isinstance(client_id, str):
            return
        
        with self._clients_lock:
            obs = []
            for obj in observables:
                ob = self._observable_factory(lua, obj)
                self._observables.add(ob)
                obs.append(ob)
            
            client = Client(client_id, session_id, obs)
        
            key = client_id
            if key in self._clients_mqtt.keys():
                self._clients_mqtt.pop(key).unlink_observables()
                
            self._clients_mqtt[key] = client
        
    def destroy_mqtt(self, client_id: str) -> None:
        if not isinstance(client_id, str):
            return
        
        with self._clients_lock:
            key = client_id
            if key not in self._clients_mqtt.keys():
                return
            
            self._clients_mqtt.pop(key).unlink_observables()

    def clear(self) -> None:
        with self._clients_lock:
            for client in self._clients_local.values():
                client.unlink_observables()
            self._clients_local.clear()

            for client in self._clients_mqtt.values():
                client.unlink_observables()
            self._clients_mqtt.clear()
            
            self._observables.clear()
            self._observables_f.clear()
            self._observables_uv.clear()
        
    def _observable_factory(self, lua, obj: str | Feature) -> Observable:
        if isinstance(obj, str):
            if obj in self._observables_uv.keys():
                return self._observables_uv[obj]
            ob = ObservableUserVariable(lua, obj)
            self._observables_uv[obj] = ob
            return ob
        
        if obj in self._observables_f.keys():
            return self._observables_f[obj]
        ob = ObservableFeature(obj)
        self._observables_f[obj] = ob
        return ob
        
    def _send_message(self, request_id: int, msg: str, ip: str, port: int) -> None:
        try:
            payload = f"resp:{self._hostip}:{hex(request_id)[2:]}:{msg}"
            self._sock.sendto(self._cipher.encrypt(payload.encode()), (ip, port))
        except IOError:
            print("Cannot send update message.")
            
    def _manager_loop(self):
        while True:
            with self._clients_lock:
                for ob in self._observables.copy():
                    if len(ob.clients) == 0:
                        self._observables.remove(ob)
                        if isinstance(ob, ObservableFeature):
                            self._observables_f.pop(ob.feature)
                        elif isinstance(ob, ObservableUserVariable):
                            self._observables_uv.pop(ob.name)
                    else:
                        ob.update()
                
                for client in list(self._clients_local.values()):
                    if client.update_flag:
                        client.update_flag = False
                        payload = f"clientReport:{client.client_id}:{fetch_values(map(lambda x: x.value(), client.observables))}"
                        self._send_message(client.session_id, payload, client.ip, client.port)
                    
                    if time.time() - client.registration_timestamp >= CLIENT_LIFE_TIME:
                        self.destroy_client(client.ip, client.port, client.client_id)
            
                for client in list(self._clients_mqtt.values()):
                    if client.update_flag:
                        client.update_flag = False
                        payload = f"clientReport:1:{fetch_values(map(lambda x: x.value(), client.observables))}"
                        self._cloud.send_update_message(client.session_id, client.client_id, payload)
                    
                    if time.time() - client.registration_timestamp >= CLIENT_LIFE_TIME:
                        self.destroy_mqtt(client.client_id)

            if self._stop_event.wait(self._client_report_interval):
                break