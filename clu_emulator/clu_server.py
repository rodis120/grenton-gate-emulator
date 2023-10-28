
import base64
import logging
import re
import socket
import threading
from typing import Any, Callable

from .cipher import CluCipher
from .commands.command import CLUCommand
from .commands.simple_handler_command import SimpleHandlerCommand
from .config import Config
from .tftpy.TftpServer import TftpServer
from .types import CommunicationType, RequestContext
from .utils import hash_function, key_derivation, parse_lua_request

GRENTON_KEY = "hd5SHpxl0N5+WEXTXlPQmw=="
GRENTON_IV = "BwYFBAMCAQAEAgkDBAEFBw=="

LUA_REQUEST_PATTERN = re.compile(r"^req:(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3}):[a-fA-F\d]{1,16}:.*")
TFTP_PATH_PATTERN = re.compile(r"^[aAmM]:\\\\.*")
    
class CluServer:
    
    lua_handler: Callable[[str], Any] | None = None
    key_change_handler: Callable[[bytes, bytes], None] | None = None
    
    def __init__(
        self,
        config: Config,
        project_key: bytes = bytes(16),
        project_iv: bytes =  bytes(16),
        config_dir: str = "config",
        hostip: str = ""
    ) -> None:
        self.config = config

        self.private_key = config.private_key
        self.clu_iv = base64.b64decode(config.clu_iv)
        self.serial_number = config.serial_number
        self.mac_address = config.mac
        
        if hostip == "":
            self.hostip = socket.gethostbyname(socket.gethostname())
        else:
            self.hostip = hostip
        
        self.project_key = project_key
        self.project_iv = project_iv
        
        self.private_cipher = CluCipher(key_derivation(self.private_key.encode()), self.clu_iv)
        self.grenton_cipher = CluCipher(GRENTON_KEY, GRENTON_IV)
        self.project_cipher = CluCipher(self.project_key, self.project_iv)
        
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listener_thread= threading.Thread(target=self._listener_loop, daemon=True)
        
        self.tftp = TftpServer(config_dir)
        self.tftp_thread = None
        self.tftp_running = False

        self.commands: dict[str, CLUCommand] = {}

        self.registerCommand(SimpleHandlerCommand("req_start_ftp", self.start_ftp, "resp:OK"))
        self.registerCommand(SimpleHandlerCommand("req_tftp_stop", self.stop_ftp, "resp:OK"))
        
    def start(self) -> None:
        self.sock.bind(("", 1234))
        self.listener_thread.start()
        
    def close(self) -> None:
        self.sock.close()
        self.stop_ftp()
        
    def start_ftp(self) -> None:
        if self.tftp_running:
            return
        
        self.tftp_thread = threading.Thread(target=self.tftp.listen, daemon=True)
        self.tftp_thread.start()
        self.tftp_running = True
        
    def stop_ftp(self) -> None:
        if not self.tftp_running or not self.tftp_thread:
            return

        self.tftp.stop(True)
        self.tftp_thread.join()
        self.tftp_running = False
        
    def set_lua_request_handler(self, handler: Callable[[int, str], Any]) -> None:
        if handler and not callable(handler):
            raise TypeError("handler must be callable")
        self.lua_handler = handler
        
    def set_project_key_change_handler(self, handler: Callable[[bytes, bytes], None]) -> None:
        if handler and not callable(handler):
            raise TypeError("handler must be callable")
        self.key_change_handler = handler

    def registerCommand(self, command: CLUCommand) -> None:
        self.commands[command.name] = command
        
    def _listener_loop(self):
        while True:
            try:
                data, sender_addr = self.sock.recvfrom(1024)
                
                try:
                    msg = self.project_cipher.decrypt(data).decode().strip()
                    
                    if LUA_REQUEST_PATTERN.match(msg):
                        self._handle_lua_request(msg, sender_addr)
                        
                    else:
                        self._handle_clu_command(msg, sender_addr)
                        
                except:
                    try:
                        msg = self.grenton_cipher.decrypt(data)
                        self._handle_clu_discovery(msg, sender_addr)
                        
                    except:
                        try:
                            msg = self.private_cipher.decrypt(data)
                            if msg.startswith(b"req_set_clu_ip"):
                                print(f"Recieved ip change request from {sender_addr[0]}:{sender_addr[1]}")
                                print("Ignoring. (Sending garbage as OM only checks the begining of the response)")
                                
                                self.sock.sendto(self.private_cipher.encrypt(b"resp_set_clu_ip:Lorem_ipsum_dolor_sit_amet"), sender_addr)
                                continue
                            
                            self._handle_set_key(msg, sender_addr)
                        except:
                            pass
                
            except Exception as e:
                logging.error(e)
         
    def _change_project_key(self, key, iv):
        self.project_key = key
        self.project_iv = iv
        self.project_cipher.set_key(self.project_key, self.project_iv)
        
        if self.key_change_handler:
            self.key_change_handler(self.project_key, self.project_iv)
            
    def _handle_lua_request(self, msg: str, sender_addr):
        session_id, payload = parse_lua_request(msg)
                        
        print(f"Received lua request from {sender_addr[0]}:{sender_addr[1]}")
        print(f"Request payload: {payload}")
        
        if self.lua_handler:
            req_context = RequestContext(session_id, sender_addr[0], sender_addr[1], None, CommunicationType.LOCAL)
            resp = self.lua_handler(req_context, payload)
            resp_message = f"resp:{self.hostip}:{session_id}:{resp}"
            
            logging.info(f"Sending response to {sender_addr[0]}:{sender_addr[1]}")
            logging.info(f"Response payload: {resp}")
            self.sock.sendto(self.project_cipher.encrypt(resp_message.encode()), sender_addr)
        
        else:
            logging.info("Ignoring request.")

    def _handle_clu_command(self, cmd: str, return_addr):
        logging.info(f'Recived clu command "{cmd}" from {return_addr[0]}:{return_addr[1]}')
        split = cmd.split(':')
        cmd = split[0]
        args = split[1:] if len(split) > 1 else []
        
        if cmd not in self.commands.keys():
            logging.info(f'"{cmd}" is not a valid command. Ignoring.')
            return

        resp = None
        handler = self.commands.get(cmd)
        if handler:
            resp = handler.execute(args)

        if resp == None:
            resp = "resp:OK"
        else:
            resp = str(resp)
        
        logging.info(f"Sending respnese to {return_addr[0]}:{return_addr[1]}")
        logging.info(f"Response: {resp}")
        self.sock.sendto(self.project_cipher.encrypt(resp.encode()), return_addr)
       
    def _handle_clu_discovery(self, payload: bytes, return_addr):
        token = payload[:32]
        sender_iv = payload[33:49]

        split = payload[50:].split(b':')
        command = split[0].decode()
        sender_ip = split[1]
        
        if command != "req_discovery_clu":
            return
        
        print(f"Received clu discovery request from {return_addr[0]}:{return_addr[1]}")
        
        sender_cipher = CluCipher(GRENTON_KEY, sender_iv)
        
        try:
            token = self.project_cipher.decrypt(token)
            token = hash_function(token)
            token = self.private_cipher.encrypt(token)
        except:
            token = bytes(32)
        
        part2 = f":resp_discovery_clu:{hex(self.serial_number)[2:]}:{self.mac_address}".encode()
        
        response_payload = token + b":" + self.clu_iv + part2
        
        encrypted = sender_cipher.encrypt(response_payload)

        self.sock.sendto(encrypted, return_addr)
        print(f"Sending clu discovery reponse to {return_addr[0]}")
        
    def _handle_set_key(self, payload: bytes, return_addr):
        iv = payload[33:49]
        
        payload = payload[50:]
        i = payload.find(b":")
        command = payload[:i].decode()
        if command != "req_set_key":
            return

        print("Received key set request")
        
        key = payload[i+1:-2]
        
        self._change_project_key(key, iv)
        self.sock.sendto(self.project_cipher.encrypt(b"resp:OK"), return_addr)
        