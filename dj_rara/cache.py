"""Small, process-local cache for Spotify metadata."""

from collections import OrderedDict
from copy import deepcopy
from threading import Lock
from time import monotonic


class SessionCache:
    def __init__(self, max_entries: int = 512, ttl: float = 600):
        self.max_entries = max_entries
        self.ttl = ttl
        self._entries: OrderedDict[tuple, tuple[float, object]] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple):
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            expires, value = entry
            if expires <= monotonic():
                del self._entries[key]
                return None
            self._entries.move_to_end(key)
            return deepcopy(value)

    def put(self, key: tuple, value) -> None:
        if value is None:
            return
        with self._lock:
            now = monotonic()
            for expired in [k for k, (expiry, _) in self._entries.items() if expiry <= now]:
                del self._entries[expired]
            self._entries[key] = (now + self.ttl, deepcopy(value))
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_entries:
                self._entries.popitem(last=False)
