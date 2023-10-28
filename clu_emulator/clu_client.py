
import random
import socket

from .cipher import CluCipher
from .utils import find_n_character, get_host_ip


def _extract_payload(resp: str) -> str:
    index = find_n_character(resp, ':', 3)
    if index == -1:
        return resp
         
    return resp[index + 1:]
        
def _generate_id_hex(lenght=8) -> str:
        return ''.join(random.choices("01234567890abcdef", k=lenght))
    
class CluClient:

    def __init__(
        self,
        ip: str,
        cipher: CluCipher,
        timeout: float = 1,
        hostip: str | None = None
    ) -> None:
        self._addr = (ip, 1234)
        self._timeout = timeout
        
        if hostip:
            self._local_ip = hostip
        else:
            self._local_ip = get_host_ip(ip)
            
        self._cipher = cipher

    def send_request(self, msg: str) -> str:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self._timeout)
        
        payload = self._cipher.encrypt(msg.encode())
        
        try:
            sock.sendto(payload, self._addr)
            resp, _ = sock.recvfrom(1024)
                
            return self._cipher.decrypt(resp).decode()
        except Exception as e:
            raise e
        finally:
            sock.close()

    def send_lua_request(self, payload):
        req_id = _generate_id_hex()
        payload = f'req:{self._local_ip}:{req_id}:(load("result = {payload} return (type(result) .. \\\":\\\" .. tostring(result))")())' # basically remote code execution
    
        resp = self.send_request(payload)
        resp = _extract_payload(resp)
        
        i = resp.find(":")
        
        resp_type = resp[:i]
        value = resp[i+1:]
        
        if resp_type == "number":
            return float(value)
        elif resp_type == "string":
            return value
        elif resp_type == "boolean":
            return value == "true"
        else:
            return None
    