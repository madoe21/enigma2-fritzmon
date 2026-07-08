# -*- coding: utf-8 -*-
"""
FritzMon – Fritz!Box TR-064 API client.

Uses the TR-064 SOAP interface to query the list of all known network
hosts (active and inactive) from the router.

This module is intentionally kept free of any Enigma2 / Kodi imports so
that it can be reused as-is in a Kodi addon or any other Python environment.
"""
from __future__ import absolute_import

import time

try:
    from urllib2 import (
        Request,
        build_opener,
        HTTPPasswordMgrWithDefaultRealm,
        HTTPDigestAuthHandler,
        URLError,
        HTTPError,
    )
except ImportError:
    from urllib.request import (
        Request,
        build_opener,
        HTTPPasswordMgrWithDefaultRealm,
        HTTPDigestAuthHandler,
    )
    from urllib.error import URLError, HTTPError

try:
    from xml.etree import cElementTree as ET
except ImportError:
    from xml.etree import ElementTree as ET

# ---------------------------------------------------------------------------
# SOAP envelope template (one-liner to avoid trailing whitespace issues)
# ---------------------------------------------------------------------------
_SOAP_TEMPLATE = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"'
    ' xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">'
    "<s:Body>"
    '<u:{action} xmlns:u="{service}">'
    "{params}"
    "</u:{action}>"
    "</s:Body>"
    "</s:Envelope>"
)


class FritzMonApiClient(object):
    """Minimal TR-064 client for querying Fritz!Box host list."""

    HOSTS_SERVICE = "urn:dslforum-org:service:Hosts:1"
    HOSTS_PATH = "/upnp/control/hosts"

    def __init__(self, host="fritz.box", port=49000, username="", password=""):
        self.host = (host or "fritz.box").strip()
        self.port = int(port) if port else 49000
        self.username = (username or "").strip()
        self.password = (password or "").strip()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_url(self):
        return "http://%s:%d" % (self.host, self.port)

    def _make_opener(self):
        if self.username or self.password:
            mgr = HTTPPasswordMgrWithDefaultRealm()
            mgr.add_password(None, self._base_url(), self.username, self.password)
            return build_opener(HTTPDigestAuthHandler(mgr))
        return build_opener()

    def _soap_call(self, path, service, action, params=""):
        url = self._base_url() + path
        body = _SOAP_TEMPLATE.format(action=action, service=service, params=params)
        if not isinstance(body, bytes):
            body = body.encode("utf-8")

        req = Request(url, data=body)
        req.add_header("Content-Type", "text/xml; charset=utf-8")
        req.add_header("SOAPAction", '"%s#%s"' % (service, action))

        opener = self._make_opener()
        response = opener.open(req, timeout=10)
        raw = response.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return ET.fromstring(raw)

    @staticmethod
    def _text(root, tag):
        """Return the text content of the first element whose local tag name matches."""
        for elem in root.iter():
            local = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if local == tag:
                return (elem.text or "").strip()
        return ""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_host_count(self):
        """Return the total number of known hosts (active + inactive)."""
        root = self._soap_call(
            self.HOSTS_PATH, self.HOSTS_SERVICE, "GetHostNumberOfEntries"
        )
        val = self._text(root, "NewHostNumberOfEntries")
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    def get_host_entry(self, index):
        """Return a dict with details for the host at the given (0-based) index."""
        params = "<NewIndex>%d</NewIndex>" % int(index)
        root = self._soap_call(
            self.HOSTS_PATH, self.HOSTS_SERVICE, "GetGenericHostEntry", params
        )
        active_raw = self._text(root, "NewActive")
        return {
            "ip": self._text(root, "NewIPAddress"),
            "mac": self._text(root, "NewMACAddress"),
            "hostname": self._text(root, "NewHostName"),
            "interface": self._text(root, "NewInterfaceType"),
            "active": active_raw == "1",
            "address_source": self._text(root, "NewAddressSource"),
        }

    def ping(self):
        """Quick connectivity check – fetch host count only.  Returns (ok, error)."""
        try:
            self.get_host_count()
            return True, None
        except URLError as exc:
            return False, "Netzwerkfehler: %s" % exc
        except HTTPError as exc:
            if exc.code == 401:
                return False, "Authentifizierung fehlgeschlagen (HTTP 401)"
            return False, "HTTP Fehler %d: %s" % (exc.code, exc.reason or "")
        except Exception as exc:
            return False, "Fehler: %s" % exc

    def fetch_hosts(self):
        """Fetch all known hosts from the Fritz!Box.

        Returns:
            (hosts, timestamp, error)
            - hosts:     list of dicts or None on fatal error
            - timestamp: int unix timestamp or None
            - error:     error string or None
        """
        try:
            count = self.get_host_count()
            hosts = []
            for i in range(count):
                try:
                    hosts.append(self.get_host_entry(i))
                except Exception:
                    # Skip malformed individual entries rather than failing all
                    pass
            return hosts, int(time.time()), None

        except URLError as exc:
            return None, None, "Netzwerkfehler: %s" % exc
        except HTTPError as exc:
            if exc.code == 401:
                return None, None, "Authentifizierung fehlgeschlagen (HTTP 401) – Benutzername/Passwort prüfen"
            return None, None, "HTTP Fehler %d: %s" % (exc.code, exc.reason or "")
        except Exception as exc:
            return None, None, "Fehler: %s" % exc
