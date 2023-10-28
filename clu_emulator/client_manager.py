
import socket
import threading
import time

from clu_emulator.objects.grenton_object import Feature

from .objects.grenton_object import Feature
from .cipher import CluCipher
from .clu_cloud import CloudCommunicator
from .utils import fetch_feature_values

CLIENT_LIFE_TIME = 60

class Client:
    
    def __init__(
        self,
        client_id: int,
        request_id: int,
        features: list[Feature]
    ) -> None:
        self.client_id = client_id
        self.request_id = request_id
        self.features = features
        self.update_flag = False
        self.registration_timestamp = time.time()
        
    def update_handler(self, value):
        self.update_flag = True
    
    def register_features(self):
        for feature in self.features:
            feature.add_value_change_handler(self.update_handler)
            
    def unregister_features(self):
        for feature in self.features:
            feature.remove_value_change_handler(self.update_handler)

class LocalClient(Client):
    
    def __init__(self, ip: str, port: int, client_id: int, request_id: int, features: list[Feature]) -> None:
        super().__init__(client_id, request_id, features)

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
    
    def register_client(self, ip: str, port: int, client_id: int, request_id: int, features: list[Feature]) -> None:
        if not (isinstance(ip, str) and isinstance(port, int) and isinstance(client_id, int)):
            return
        
        with self._clients_lock:
            client = LocalClient(ip, port, client_id, request_id, features)
        
            key = (ip, port, client_id)
            if key in self._clients_local.keys():
                self._clients_local.pop(key).unregister_features()
                
            self._clients_local[key] = client
            client.register_features()
        
    def destroy_client(self, ip: str, port: int, client_id: int) -> None:
        if not (isinstance(ip, str) and isinstance(port, int) and isinstance(client_id, int)):
            return
        
        with self._clients_lock:
            key = (ip, port, client_id)
            if key not in self._clients_local.keys():
                return
            
            client = self._clients_local.pop(key)
            client.unregister_features()
            
    def register_mqtt(self, client_id: str, request_id: int, features: list[Feature]) -> None:
        if not isinstance(client_id, str):
            return
        
        with self._clients_lock:
            client = Client(client_id, request_id, features)
        
            key = client_id
            if key in self._clients_mqtt.keys():
                self._clients_mqtt.pop(key).unregister_features()
                
            self._clients_mqtt[key] = client
            client.register_features()
        
    def destroy_mqtt(self, client_id: str) -> None:
        if not isinstance(client_id, str):
            return
        
        with self._clients_lock:
            key = client_id
            if key not in self._clients_mqtt.keys():
                return
            
            client = self._clients_mqtt.pop(key)
            client.unregister_features()

    def clear(self) -> None:
        with self._clients_lock:
            for client in self._clients_local.values():
                client.unregister_features()
            self._clients_local.clear()

            for client in self._clients_mqtt.values():
                client.unregister_features()
            self._clients_mqtt.clear()
        
    def _send_message(self, request_id: int, msg: str, ip: str, port: int) -> None:
        try:
            payload = f"resp:{self._hostip}:{hex(request_id)[2:]}:{msg}"
            self._sock.sendto(self._cipher.encrypt(payload.encode()), (ip, port))
        except IOError:
            print("Cannot send update message.")
            
    def _manager_loop(self):
        while True:
            with self._clients_lock:
                for client in list(self._clients_local.values()):
                    if client.update_flag:
                        client.update_flag = False
                        payload = f"clientReport:{client.client_id}:{fetch_feature_values(client.features)}"
                        self._send_message(client.request_id, payload, client.ip, client.port)
                    
                    if time.time() - client.registration_timestamp >= CLIENT_LIFE_TIME:
                        self.destroy_client(client.ip, client.port, client.client_id)
            
                for client in list(self._clients_mqtt.values()):
                    if client.update_flag:
                        client.update_flag = False
                        payload = f"clientReport:1:{fetch_feature_values(client.features)}"
                        self._cloud.send_update_message(client.request_id, client.client_id, payload)
                    
                    if time.time() - client.registration_timestamp >= CLIENT_LIFE_TIME:
                        self.destroy_mqtt(client.client_id)

            if self._stop_event.wait(self._client_report_interval):
                break