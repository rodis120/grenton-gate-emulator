from dataclasses import dataclass
from enum import Enum


class CommunicationType(Enum):
    LOCAL = "local"
    CLOUD = "cloud"

@dataclass
class RequestContext:
    session_id: int
    ip: str
    port: int
    client_id: str
    comm_type: CommunicationType