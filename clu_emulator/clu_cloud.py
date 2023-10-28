
import time
from typing import Callable

import paho.mqtt.client as mqtt

from .cipher import CluCipher
from .config import Config
from .types import CommunicationType, RequestContext
from .utils import parse_lua_request


CLOUD_ENCPOINT = "a20a1h6d1nekft-ats.iot.eu-central-1.amazonaws.com"

class CloudCommunicator:
    
    def __init__(self, config: Config, cipher: CluCipher) -> None:
        self._config = config
        self._cipher = cipher
        
        self._client = mqtt.Client(client_id=f"emulator_{config.serial_number}")
        self._client.tls_set(certfile="config/cert.pem", keyfile="config/key.pem")
        
        self._client.on_disconnect = self._on_disconect
            
        self._client.connect(CLOUD_ENCPOINT, 8883)
        self._client.loop_start()
        
        self._client.on_message = self._on_message
        self._client.subscribe(topic=f"clu/{config.serial_number}/inbound/+")
        
        self._request_handler = lambda x, y: None
        
    def set_request_handler(self, request_handler: Callable[[int, str], str]) -> None:
        self._request_handler = request_handler
        
    def send_update_message(self, request_id: int, client_id: str, payload: str) -> None:
        payload = f"resp:0.0.0.0:{hex(request_id)[2:]}:{payload}"
        print(payload)
        payload = self._cipher.encrypt(payload.encode())
        self._client.publish(topic=f"clu/{self._config.serial_number}/outbound/{client_id}", payload=payload)
    
    def _on_disconect(self, client: mqtt.Client, userdata, rs) -> None:
        while True:
            time.sleep(1000)
            try:
                client.reconnect()
                return
            except:
                pass
    
    def _on_message(self, client: mqtt.Client, userdata, message: mqtt.MQTTMessage) -> None:
        topic = message.topic
        payload = message.payload
        
        client_id = topic.split('/')[-1]
        
        try:
            payload = self._cipher.decrypt(payload).decode()
            print(payload)
            session_id, req = parse_lua_request(payload)
            req_context = RequestContext(session_id, None, None, client_id, CommunicationType.CLOUD)
            resp = f"resp:127.0.0.1:{hex(session_id)[2:]}:{self._request_handler(req_context, req)}" 
            print(resp)
            resp = self._cipher.encrypt(resp.encode())
            
            client.publish(topic=f"clu/{self._config.serial_number}/outbound/{client_id}", payload=resp)
        except:
            pass
