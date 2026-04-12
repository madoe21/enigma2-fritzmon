# -*- coding: utf-8 -*-
from __future__ import absolute_import

import json
import os
import time

CACHE_FILE = "/etc/enigma2/fritzmon_cache.json"


class FritzMonStore(object):
    """Simple JSON-file cache for the host list."""

    def __init__(self, cache_file=CACHE_FILE):
        self.cache_file = cache_file

    def _read(self):
        try:
            with open(self.cache_file, "r") as fh:
                data = json.load(fh)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _write(self, data):
        folder = os.path.dirname(self.cache_file)
        if folder and not os.path.isdir(folder):
            try:
                os.makedirs(folder)
            except Exception:
                pass
        try:
            with open(self.cache_file, "w") as fh:
                json.dump(data, fh, indent=2, sort_keys=True)
        except Exception:
            pass

    def save(self, hosts, host_key):
        self._write(
            {
                "updated": int(time.time()),
                "host_key": str(host_key),
                "hosts": hosts or [],
            }
        )

    def load(self):
        data = self._read()
        if not isinstance(data.get("hosts"), list):
            data["hosts"] = []
        return data
