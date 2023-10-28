
from dataclasses import dataclass


@dataclass
class Config:
    serial_number: int
    mac: str
    private_key: str

    velux_ip: str
    velux_password: str

    hw_type: int = 18
    hw_ver: int = 2
    fw_type: int = 3
    fw_api_ver: int = 1300
    fw_ver: str = "1.3.1-2243"

    clu_iv: str = "AAAAAAAAAAAAAAAAAAAAAA=="


