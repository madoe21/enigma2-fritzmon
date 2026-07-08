# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os

from Components.config import (
    ConfigInteger,
    ConfigSubsection,
    ConfigText,
    ConfigYesNo,
    config,
)


class ConfigPassword(ConfigText):
    """ConfigText variant that displays asterisks instead of clear text."""

    def getText(self):
        return u"*" * len(self.value) if self.value else u""

    def getMulti(self, selected):
        mtext = u"*" * len(self.value) if self.value else u""
        if selected:
            return ("mtext", mtext + u"_")
        return ("mtext", mtext)
from Plugins.Plugin import PluginDescriptor
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

from . import _
from .core.api import FritzMonApiClient
from .screens import FritzMonMainScreen, FritzMonSettingsScreen
from .core.store import FritzMonStore

SETTINGS_FILE = "/etc/enigma2/settings"
USE_ASPECT_ICON_VARIANTS = True

if not hasattr(config.plugins, "fritzmon"):
    config.plugins.fritzmon = ConfigSubsection()

config.plugins.fritzmon.host = ConfigText(default="fritz.box", fixed_size=False)
config.plugins.fritzmon.port = ConfigInteger(default=49000, limits=(1, 65535))
config.plugins.fritzmon.username = ConfigText(default="", fixed_size=False)
config.plugins.fritzmon.password = ConfigPassword(default="", fixed_size=False)
config.plugins.fritzmon.show_inactive = ConfigYesNo(default=True)


class AppContext(object):
    """Central application object – holds config, store and API client.

    Kept framework-agnostic in its data layer so it can be ported to Kodi
    without changes.  Screen-level glue lives in screens.py.
    """

    def __init__(self):
        self._load_settings_from_file()
        self.store = FritzMonStore()
        self.api = self._make_api()

    # ------------------------------------------------------------------
    # Settings helpers
    # ------------------------------------------------------------------

    def _load_settings_from_file(self):
        """Read persisted Enigma2 settings so values are available on first
        launch before the config system has fully initialised."""
        if not os.path.exists(SETTINGS_FILE):
            return
        values = {}
        try:
            with open(SETTINGS_FILE, "r") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or not line.startswith("config.plugins.fritzmon."):
                        continue
                    if "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    values[key] = value.strip()
        except Exception:
            return

        host = values.get("config.plugins.fritzmon.host")
        port = values.get("config.plugins.fritzmon.port")
        username = values.get("config.plugins.fritzmon.username")
        password = values.get("config.plugins.fritzmon.password")
        show_inactive = values.get("config.plugins.fritzmon.show_inactive")

        if host:
            config.plugins.fritzmon.host.value = host
        if port:
            try:
                config.plugins.fritzmon.port.value = int(port)
            except Exception:
                pass
        if username is not None:
            config.plugins.fritzmon.username.value = username
        if password is not None:
            config.plugins.fritzmon.password.value = password
        if show_inactive is not None:
            config.plugins.fritzmon.show_inactive.value = show_inactive.lower() in ("true", "1", "yes")

    def _make_api(self):
        return FritzMonApiClient(
            host=self.get_host(),
            port=self.get_port(),
            username=self.get_username(),
            password=self.get_password(),
        )

    def _rebuild_api(self):
        self.api = self._make_api()

    def get_host(self):
        return (config.plugins.fritzmon.host.value or "fritz.box").strip()

    def get_port(self):
        try:
            p = int(config.plugins.fritzmon.port.value)
            return p if 1 <= p <= 65535 else 49000
        except Exception:
            return 49000

    def get_username(self):
        return (config.plugins.fritzmon.username.value or "").strip()

    def get_password(self):
        return (config.plugins.fritzmon.password.value or "").strip()

    def get_show_inactive(self):
        return bool(config.plugins.fritzmon.show_inactive.value)

    def settings_complete(self):
        return bool(self.get_host())

    def cache_host_key(self):
        return "%s:%d" % (self.get_host(), self.get_port())

    # ------------------------------------------------------------------
    # Data operations
    # ------------------------------------------------------------------

    def refresh_hosts(self):
        """Fetch fresh host list; fall back to cache on error.

        Returns a dict:
          {
            "hosts":      list of host dicts,
            "updated":    unix timestamp or None,
            "error":      error string or None,
            "from_cache": bool,
          }
        """
        self._rebuild_api()
        hosts, updated, error = self.api.fetch_hosts()
        if hosts is not None:
            self.store.save(hosts, self.cache_host_key())
            return {"hosts": hosts, "updated": updated, "error": None, "from_cache": False}

        # Fall back to cache
        cache = self.store.load()
        cached_hosts = cache.get("hosts") or []
        if cached_hosts:
            return {
                "hosts": cached_hosts,
                "updated": cache.get("updated"),
                "error": error,
                "from_cache": True,
            }

        return {"hosts": [], "updated": updated, "error": error, "from_cache": False}

    def ping(self):
        self._rebuild_api()
        return self.api.ping()


# ---------------------------------------------------------------------------
# Enigma2 plugin entry points
# ---------------------------------------------------------------------------

_APP = None


def get_app():
    global _APP
    if _APP is None:
        _APP = AppContext()
    return _APP


def main(session, **kwargs):
    app = get_app()
    if app.settings_complete():
        session.open(FritzMonMainScreen, app)
    else:
        session.open(FritzMonSettingsScreen, app, True)


def _icon_file_for_aspect_ratio():
    try:
        from enigma import getDesktop

        sz = getDesktop(0).size()
        width = int(sz.width())
        height = int(sz.height())
        if height > 0:
            ratio = float(width) / float(height)
            if ratio < 1.5:
                return "plugin_4x3.png"
            if ratio < 1.7:
                return "plugin_16x10.png"
            return "plugin_16x9.png"
    except Exception:
        pass
    return "plugin_16x9.png"


def _resolve_plugin_icon_path():
    if not USE_ASPECT_ICON_VARIANTS:
        return resolveFilename(SCOPE_PLUGINS, "Extensions/fritz_mon/res/plugin.png")
    icon_name = _icon_file_for_aspect_ratio()
    icon_path = resolveFilename(SCOPE_PLUGINS, "Extensions/fritz_mon/res/%s" % icon_name)
    if os.path.exists(icon_path):
        return icon_path
    return resolveFilename(SCOPE_PLUGINS, "Extensions/fritz_mon/res/plugin.png")


def Plugins(**kwargs):
    plugin_icon = _resolve_plugin_icon_path()
    return [
        PluginDescriptor(
            name=_("FritzMon"),
            description=_("FritzMon - Network Overview"),
            where=PluginDescriptor.WHERE_PLUGINMENU,
            icon=plugin_icon,
            fnc=main,
        )
    ]
