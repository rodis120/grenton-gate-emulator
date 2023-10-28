
import json

from pyvlx.pyvlx import Config

from .clu_cloud import CloudCommunicator
from .client_manager import ClientManager
from .clu_lua_engine import CluLuaEngine
from .clu_server import CluServer
from .commands.simple_handler_command import SimpleHandlerCommand
from .config import Config
from .config_manager import ConfigManager
from .module_manager import Module, ModuleInfo, ModuleManager


def load_config(config_file) -> Config:
    with open(config_file, "r") as f:
        return json.load(f, object_hook=lambda x: Config(**x))

class CluEmulator:
    
    def __init__(self, config_file, config_dir: str = "config") -> None:
        self.config = load_config(config_file)
        self.config_dir = config_dir

        self.module_manager = ModuleManager(self.config)
        self.module_manager.add_module(Module(ModuleInfo(123, 21, 1, 2, 1, "1.3.13")))

        self.config_manager = ConfigManager(self.config, config_dir, self.module_manager)
        
        project_key, project_iv = self.config_manager.load_project_key()
        
        self.clu_server = CluServer(self.config, project_key, project_iv, config_dir)
        self.clu_cloud = CloudCommunicator(self.config, self.clu_server.project_cipher)
        self.client_manager = ClientManager(self.clu_server.project_cipher, self.clu_cloud)
        self.lua_engine = CluLuaEngine(self.config, self.client_manager, self.clu_server.project_cipher, config_dir)
        self.clu_server.set_project_key_change_handler(self.config_manager.save_project_key)
        self.clu_server.set_lua_request_handler(self.lua_engine.execute)
        self.clu_cloud.set_request_handler(self.lua_engine.execute)

        self.clu_server.registerCommand(SimpleHandlerCommand("req_reset", self.lua_engine.reload, "resp_reset"))
        self.clu_server.registerCommand(SimpleHandlerCommand("req_gen_measurements", lambda *args: self.clu_server.start_ftp(), "ok"))
        self.clu_server.registerCommand(SimpleHandlerCommand("meas_file_download", lambda *args: self.clu_server.stop_ftp(), "ok"))

    def start(self):
        self.clu_server.start()
        