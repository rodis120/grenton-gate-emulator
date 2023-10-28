
from typing import Any, Callable

class Feature:
    
    def __init__(self, data_type, gettable: bool=True, settable: bool=True, initial_value=None) -> None:
        self.data_type = data_type
        self.gettable = gettable
        self.settable = settable
        
        self.value = initial_value
        
        self._update_handlers: set[Callable] = set()
        
    def set_value(self, value, force=False) -> None:
        if self.settable or force:
            prev_value = self.value
            self.value = value
        
            if prev_value != value:
                for handler in self._update_handlers:
                    handler(value)
    
    def get_value(self) -> Any:
        if self.gettable:
            return self.value
        
    def add_value_change_handler(self, handler: Callable[[Any], None]) -> None:
        if self.gettable:
            self._update_handlers.add(handler)
        
    def remove_value_change_handler(self, handler: Callable[[Any], None]) -> None:
        if handler in self._update_handlers:
            self._update_handlers.remove(handler)
            
class DummyFeature:
    
    def set_value(self) -> None:
        pass
    
    def get_value(self) -> Any:
        return None
    
    def add_value_change_handler(self, handler: Callable[[], None]) -> None:
        pass
    
    def remove_value_change_handler(self, handler: Callable[[], None]) -> None:
        pass