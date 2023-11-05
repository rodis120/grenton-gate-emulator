
import socket

import lupa.lua53 as lupa

from .objects.feature import DummyFeature

def find_n_character(string: str, char: str, n: int) -> int:
    count = 0
    for index, c in enumerate(string):
        if c == char:
            count += 1
            if count == n:
                return index
            
    return -1

def hash_function(randomBytes: bytes) -> bytes:
    length = len(randomBytes)
    out = bytearray(length)
    
    out[0] = randomBytes[0] ^ randomBytes[length-1]
    
    for i in range(1, length):
        out[i] = (1 + (out[i-1] % 13)) * (1 + (randomBytes[i] % 19))
        
    return bytes(out)

def key_derivation(secret_key: bytes) -> bytes:
    derivation_constant = bytes.fromhex("b9afe387f919a3d3a0d79ade8e11a116") #base64 ua/jh/kZo9Og15rejhGhFg==
    out = bytearray(16)
    for i in range(8):
        out[i] = derivation_constant[i] ^ secret_key[i]
    for i in range(8):
        out[i + 8] = derivation_constant[i + 8] ^ secret_key[7 - i]
    return bytes(out)

def parse_observables_list(obs) -> list:
    values = []
    for elm in obs.values():
        if isinstance(elm, str):
            values.append(elm)
            continue
        
        elm = list(elm.values())
        obj = elm[0]
        index = elm[1]
        
        values.append(obj.features.get(index, DummyFeature()))
        
    return values

def fetch_values(values: list) -> str:
    out = []
    for value in values:
        if isinstance(value, str):
            out.append(f'"{value}"')
        elif isinstance(value, bool):
            out.append("true" if value else "false")
        elif value is None:
            out.append("nil")
        else:
            out.append(str(value))
    
    return '{' + ','.join(out) + '}'

def int_to_ip(ip_int: int) -> str:
    segments = []
    while ip_int > 0:
        segments.append(str(ip_int & 0xff))
        ip_int >>= 8
        
    segments.reverse()
        
    return '.'.join(segments)
    
def get_host_ip(clu_ip: str) -> str:
    _, _, ips = socket.gethostbyname_ex(socket.gethostname())

    for ip in ips:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, 0))
        
        try:
            sock.sendto(b"", (clu_ip, 1234))
            return ip
        except:
            pass
        
    #TODO: throw exception when no ip found
    return ""

def padd_string(string: str, length=8):
    if len(string) >= length:
        return string

    return "0" * (length - len(string)) + string

def parse_lua_request(request: str) -> tuple[int, str]:
    i = find_n_character(request, ':', 2)
    request = request[i+1:]
    i = request.find(':')

    session_id = int(request[:i], 16)
    payload = request[i+1:]
    
    return session_id, payload.strip()