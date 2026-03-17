"""
Rate limiter en memoria.
"""
import time
from typing import Optional, Tuple


class RateLimiter:
    """Rate limiter simple en memoria."""
    
    def __init__(self, window: int = 60):
        self.store = {}  # {key: (count, reset_time)}
        self.window = window
    
    def check(self, key: str, max_requests: int) -> Tuple[bool, Optional[int]]:
        """
        Verificar si una petición está permitida.
        
        Returns:
            (allowed, retry_after): Si está permitido y segundos hasta retry
        """
        now = time.time()
        
        if key in self.store:
            count, reset_time = self.store[key]
            
            if now > reset_time:
                # Reset window
                self.store[key] = (1, now + self.window)
                return True, None
            elif count >= max_requests:
                retry_after = int(reset_time - now)
                return False, retry_after
            else:
                self.store[key] = (count + 1, reset_time)
                return True, None
        else:
            self.store[key] = (1, now + self.window)
            return True, None
    
    def reset(self, key: str):
        """Resetear contador para una key."""
        if key in self.store:
            del self.store[key]
