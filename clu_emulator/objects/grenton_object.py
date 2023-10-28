
from typing import Any, Callable

from .feature import Feature


class GrentonObject:
    
    features: dict[int, Feature]
    methods: dict[int, Callable]
    
    event_handlers: dict[int, list[Callable[[], None]]]
    
    def __init__(self, engine, args) -> None:
        self.engine = engine
        self.features = {}
        self.methods = {}
        self.event_handlers = {}
    
    def get(self, index) -> Any | None:
        feature = self.features.get(index, None)
        if feature and feature.gettable:
            return feature.get_value()
    
    def set(self, index, value):
        feature = self.features.get(index, None)
        if feature:
            feature.set_value(value, not self.engine.initialized)
    
    def execute(self, index, *args):
        method = self.methods.get(index, None)
        if method:
            try:
                return method(*args)
            except:
                return None
        
        return None
    
    def add_event(self, index, handler):
        if index not in self.event_handlers.keys():
            self.event_handlers[index] = [handler]
        else:    
            self.event_handlers[index].append(handler)
        
    def fire_event(self, index) -> None:
        handlers = self.event_handlers.get(index)
        if handlers:
            for handler in handlers:
                handler()

class ModuleObject:
    
    def __init__(self, engine, args) -> None:
        self.engine = engine
        self.serial_number = args[0]
        self.module_type = args[1]