# -*- coding: utf-8 -*-
from __future__ import absolute_import

import os
import time

from Components.ActionMap import ActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.MenuList import MenuList
from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from Components.ScrollLabel import ScrollLabel
from Components.Sources.StaticText import StaticText
from Components.config import config, configfile, getConfigListEntry
from Screens.ChoiceBox import ChoiceBox
from Screens.MessageBox import MessageBox
from Screens.Screen import Screen
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

try:
    from enigma import (
        RT_HALIGN_LEFT,
        RT_HALIGN_RIGHT,
        RT_VALIGN_CENTER,
        eListboxPythonMultiContent,
        gFont,
    )
except Exception:
    RT_HALIGN_LEFT = 0
    RT_HALIGN_RIGHT = 0
    RT_VALIGN_CENTER = 0
    eListboxPythonMultiContent = None
    gFont = None

try:
    from Components.Input import Input
    from Screens.InputBox import InputBox
except Exception:
    Input = None
    InputBox = None

from . import _

SUPPORT_LINE = "Buy me a coffee: https://buymeacoffee.com/madoe21"

# ---------------------------------------------------------------------------
# Column layout constants (pixels, relative to list widget left edge)
# ---------------------------------------------------------------------------
_COL_STATUS_X = 0
_COL_STATUS_W = 40
_COL_HOST_X = 44
_COL_HOST_W = 360
_COL_IP_X = 410
_COL_IP_W = 200
_COL_TYPE_X = 618
_COL_TYPE_W = 140
_COL_MAC_X = 766
_COL_MAC_W = 190
_ROW_H = 36


def _interface_label(iface):
    """Translate TR-064 interface type string to a human-readable label."""
    if not iface:
        return _("unknown")
    lower = iface.lower()
    if "802.11" in lower or "wifi" in lower or "wlan" in lower or "wireless" in lower:
        return _("WiFi")
    if "ethernet" in lower or "eth" in lower:
        return _("Ethernet")
    return iface


def _status_char(active):
    return u"\u25cf" if active else u"\u25cb"  # ● / ○


# ===========================================================================
# Main screen
# ===========================================================================

class FritzMonMainScreen(Screen):
    CACHE_MAX_AGE = 300  # seconds before auto-refresh

    skin = """
        <screen name="FritzMonMainScreen" position="center,90" size="1180,640" title="FritzMon">
            <widget source="title" render="Label" position="20,10" size="1140,36" font="Regular;30" />
            <widget name="updated" position="20,52" size="560,28" font="Regular;22" />
            <widget name="filter_mode" position="600,52" size="560,28" font="Regular;22" halign="right" />
            <widget name="header_status" position="20,84" size="40,28" font="Regular;20" />
            <widget name="header_host" position="64,84" size="360,28" font="Regular;20" />
            <widget name="header_ip" position="430,84" size="200,28" font="Regular;20" />
            <widget name="header_type" position="638,84" size="140,28" font="Regular;20" />
            <widget name="header_mac" position="786,84" size="190,28" font="Regular;20" />
            <widget name="list" position="20,116" size="1140,430" scrollbarMode="showOnDemand" />
            <widget source="support" render="Label" position="20,553" size="1140,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,585" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="250,585" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="480,585" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/blue.png" position="710,585" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,585" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_green" render="Label" position="250,585" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_yellow" render="Label" position="480,585" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_blue" render="Label" position="710,585" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session, app):
        Screen.__init__(self, session)
        self.app = app
        self._all_hosts = []
        self._filter_active_only = not app.get_show_inactive()
        self._use_multicontent = eListboxPythonMultiContent is not None

        self["title"] = StaticText(_("FritzMon - Network Overview"))
        self["updated"] = Label(_("Updated") + ": -")
        self["filter_mode"] = Label("")
        self["header_status"] = Label(_("Status")[:1])
        self["header_host"] = Label(_("Hostname"))
        self["header_ip"] = Label(_("IP Address"))
        self["header_type"] = Label(_("Connection"))
        self["header_mac"] = Label(_("MAC Address"))

        if self._use_multicontent:
            self["list"] = MenuList([], content=eListboxPythonMultiContent)
        else:
            self["list"] = MenuList([])

        if gFont is not None:
            try:
                self["list"].l.setFont(0, gFont("Regular", 22))
                self["list"].l.setItemHeight(_ROW_H)
            except Exception:
                pass

        self["support"] = StaticText(SUPPORT_LINE)
        self["key_red"] = StaticText(_("Close"))
        self["key_green"] = StaticText(_("Refresh"))
        self["key_yellow"] = StaticText(_("Settings"))
        self["key_blue"] = StaticText(_("Information"))

        self["actions"] = ActionMap(
            ["ColorActions", "OkCancelActions", "DirectionActions", "MenuActions"],
            {
                "ok": self._open_detail,
                "cancel": self.close,
                "red": self.close,
                "green": self.action_refresh,
                "yellow": self.open_settings,
                "blue": self.open_info,
                "left": self.toggle_filter,
                "right": self.toggle_filter,
                "menu": self.open_main_menu,
            },
            -1,
        )

        self._initial_load_done = False
        self.onShow.append(self._on_show)

    def _on_show(self):
        if not self._initial_load_done:
            self._initial_load_done = True
            self.load_initial_data()

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def load_initial_data(self):
        if not self.app.settings_complete():
            self.session.open(FritzMonSettingsScreen, self.app, True)
            return

        cache = self.app.store.load()
        cached_hosts = cache.get("hosts") or []
        if cached_hosts:
            self._all_hosts = cached_hosts
            self._render()
            self._set_updated(cache.get("updated"))
            try:
                age = max(0, int(time.time()) - int(cache.get("updated") or 0))
            except Exception:
                age = self.CACHE_MAX_AGE + 1
            if age <= self.CACHE_MAX_AGE:
                return

        self.action_refresh(show_cache_info=False)

    def action_refresh(self, show_cache_info=True):
        if not self.app.settings_complete():
            self.session.open(FritzMonSettingsScreen, self.app, True)
            return

        self["updated"].setText(_("Loading..."))
        result = self.app.refresh_hosts()
        self._all_hosts = result.get("hosts") or []
        self._render()
        self._set_updated(result.get("updated"))

        if show_cache_info and result.get("from_cache"):
            msg = _("Using cached data")
            if result.get("error"):
                msg = "%s\n(%s)" % (msg, result.get("error"))
            self.session.open(MessageBox, msg, MessageBox.TYPE_INFO, timeout=5)
        elif result.get("error") and not self._all_hosts:
            self.session.open(
                MessageBox,
                _("Error") + ": " + str(result.get("error")),
                MessageBox.TYPE_ERROR,
                timeout=6,
            )

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _visible_hosts(self):
        if self._filter_active_only:
            return [h for h in self._all_hosts if h.get("active")]
        return list(self._all_hosts)

    def _render(self):
        hosts = self._visible_hosts()
        # Sort: active devices first, then alphabetically by hostname
        hosts.sort(key=lambda h: (0 if h.get("active") else 1, (h.get("hostname") or "").lower()))

        self._rendered_hosts = hosts
        self._update_filter_label()

        if not hosts:
            empty_label = _("No devices found")
            if self._use_multicontent:
                self["list"].setList(
                    [
                        [
                            None,
                            MultiContentEntryText(
                                pos=(0, 0),
                                size=(1140, _ROW_H),
                                font=0,
                                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                                text=empty_label,
                            ),
                        ]
                    ]
                )
            else:
                self["list"].setList([empty_label])
            return

        if self._use_multicontent:
            self["list"].setList([self._build_item(h) for h in hosts])
        else:
            self["list"].setList([self._format_plain(h) for h in hosts])

    def _build_item(self, host):
        status = _status_char(host.get("active", False))
        hostname = (host.get("hostname") or "-")[:36]
        ip = (host.get("ip") or "-")[:18]
        iface = _interface_label(host.get("interface") or "")
        mac = (host.get("mac") or "-").upper()
        color = 0x00CC00 if host.get("active") else 0x888888

        return [
            host,
            MultiContentEntryText(
                pos=(_COL_STATUS_X, 0),
                size=(_COL_STATUS_W, _ROW_H),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=status,
                color=color,
            ),
            MultiContentEntryText(
                pos=(_COL_HOST_X, 0),
                size=(_COL_HOST_W, _ROW_H),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=hostname,
                color=color,
            ),
            MultiContentEntryText(
                pos=(_COL_IP_X, 0),
                size=(_COL_IP_W, _ROW_H),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=ip,
                color=color,
            ),
            MultiContentEntryText(
                pos=(_COL_TYPE_X, 0),
                size=(_COL_TYPE_W, _ROW_H),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=iface,
                color=color,
            ),
            MultiContentEntryText(
                pos=(_COL_MAC_X, 0),
                size=(_COL_MAC_W, _ROW_H),
                font=0,
                flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER,
                text=mac,
                color=color,
            ),
        ]

    def _format_plain(self, host):
        status = "+" if host.get("active") else "-"
        hostname = (host.get("hostname") or "-")[:30]
        ip = (host.get("ip") or "-")[:15]
        iface = _interface_label(host.get("interface") or "")[:9]
        return "[%s] %-30s  %-15s  %-9s" % (status, hostname, ip, iface)

    def _set_updated(self, ts):
        if not ts:
            self["updated"].setText(_("Updated") + ": -")
            return
        formatted = time.strftime("%d.%m.%Y %H:%M:%S", time.localtime(int(ts)))
        total = len(self._all_hosts)
        active = sum(1 for h in self._all_hosts if h.get("active"))
        self["updated"].setText(
            _("Updated") + ": %s  |  %d %s (%d %s)"
            % (formatted, active, _("active"), total, _("Devices"))
        )

    def _update_filter_label(self):
        if self._filter_active_only:
            self["filter_mode"].setText(_("Filter") + ": " + _("Active only"))
        else:
            self["filter_mode"].setText(_("Filter") + ": " + _("All devices"))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def _get_selected_host(self):
        if not hasattr(self, "_rendered_hosts") or not self._rendered_hosts:
            return None
        try:
            index = int(self["list"].getSelectionIndex())
        except Exception:
            try:
                index = int(self["list"].getSelectedIndex())
            except Exception:
                index = 0
        if index < 0 or index >= len(self._rendered_hosts):
            return None
        return self._rendered_hosts[index]

    def _open_detail(self):
        host = self._get_selected_host()
        if not host:
            self.session.open(
                MessageBox, _("No devices found"), MessageBox.TYPE_INFO, timeout=3
            )
            return
        self.session.open(FritzMonDetailScreen, host)

    def toggle_filter(self):
        self._filter_active_only = not self._filter_active_only
        self._render()

    def open_settings(self):
        self.session.openWithCallback(
            lambda *_: self.load_initial_data(),
            FritzMonSettingsScreen,
            self.app,
            False,
        )

    def open_info(self):
        self.session.open(FritzMonInfoScreen)

    def open_main_menu(self):
        options = [
            (_("Close"), "close"),
            (_("Refresh"), "refresh"),
            (_("Filter") + ": " + _("Active only"), "filter_active"),
            (_("Filter") + ": " + _("All devices"), "filter_all"),
            (_("Settings"), "settings"),
            (_("Information"), "info"),
        ]
        self.session.openWithCallback(
            self._on_menu_choice,
            ChoiceBox,
            title=_("Main menu"),
            list=options,
        )

    def _on_menu_choice(self, choice=None):
        if not choice:
            return
        action = choice[1]
        if action == "close":
            self.close()
        elif action == "refresh":
            self.action_refresh()
        elif action == "filter_active":
            self._filter_active_only = True
            self._render()
        elif action == "filter_all":
            self._filter_active_only = False
            self._render()
        elif action == "settings":
            self.open_settings()
        elif action == "info":
            self.open_info()


# ===========================================================================
# Detail screen
# ===========================================================================

class FritzMonDetailScreen(Screen):
    skin = """
        <screen name="FritzMonDetailScreen" position="center,120" size="900,500" title="FritzMon - Gerät">
            <widget source="title" render="Label" position="20,10" size="860,40" font="Regular;32" />
            <widget name="body" position="20,60" size="860,360" font="Regular;26" scrollbarMode="showOnDemand" />
            <widget source="support" render="Label" position="20,430" size="860,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,460" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,460" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session, host):
        Screen.__init__(self, session)
        self._host = host or {}

        hostname = (self._host.get("hostname") or _("n/a")).strip()
        self["title"] = StaticText(hostname)
        self["body"] = ScrollLabel(self._build_text())
        self["support"] = StaticText(SUPPORT_LINE)
        self["key_red"] = StaticText(_("Close"))

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "red": self.close,
                "up": self["body"].pageUp,
                "down": self["body"].pageDown,
            },
            -1,
        )

    def _build_text(self):
        h = self._host
        active_str = _("active") if h.get("active") else _("inactive")
        iface = _interface_label(h.get("interface") or "")
        source = (h.get("address_source") or _("n/a")).strip()
        mac = (h.get("mac") or _("n/a")).upper()
        ip = h.get("ip") or _("n/a")
        hostname = (h.get("hostname") or _("n/a")).strip()

        lines = [
            _("Hostname") + ":         " + hostname,
            _("IP Address") + ":       " + ip,
            _("MAC Address") + ":      " + mac,
            _("Status") + ":           " + active_str,
            _("Connection") + ":       " + iface,
            _("Address Source") + ":   " + source,
            _("Interface Type") + ":   " + (h.get("interface") or _("n/a")),
        ]
        return "\n".join(lines)


# ===========================================================================
# Settings screen
# ===========================================================================

class FritzMonSettingsScreen(Screen, ConfigListScreen):
    skin = """
        <screen name="FritzMonSettingsScreen" position="center,100" size="980,560" title="FritzMon Einstellungen">
            <widget source="title" render="Label" position="20,10" size="940,36" font="Regular;30" />
            <widget name="config" position="20,56" size="940,330" scrollbarMode="showOnDemand" />
            <widget source="hint" render="Label" position="20,396" size="940,60" font="Regular;20" />
            <widget source="support" render="Label" position="20,464" size="940,24" font="Regular;18" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,500" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/green.png" position="250,500" size="220,30" alphatest="on" />
            <ePixmap pixmap="skin_default/buttons/yellow.png" position="480,500" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,500" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_green" render="Label" position="250,500" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
            <widget source="key_yellow" render="Label" position="480,500" size="220,30" font="Regular;22" halign="center" valign="center" transparent="1" />
        </screen>
    """

    _HELP = {
        "host": "Enter Fritz!Box hostname or IP address",
        "port": "Enter the TR-064 port (default: 49000)",
        "username": "Enter Fritz!Box username (leave empty if none)",
        "password": "Enter Fritz!Box password",
        "show_inactive": "Show all known devices (active and inactive)",
    }

    def __init__(self, session, app, open_main_on_save):
        Screen.__init__(self, session)
        self.app = app
        self.open_main_on_save = bool(open_main_on_save)

        self["title"] = StaticText(_("Fritz!Box Settings"))
        self["hint"] = StaticText("")
        self["support"] = StaticText(SUPPORT_LINE)
        self["key_red"] = StaticText(_("Cancel"))
        self["key_green"] = StaticText(_("Save"))
        self["key_yellow"] = StaticText(_("Test connection"))

        self._entries = [
            getConfigListEntry(_("Fritz!Box Host/IP"), config.plugins.fritzmon.host),
            getConfigListEntry(_("Port"), config.plugins.fritzmon.port),
            getConfigListEntry(_("Username"), config.plugins.fritzmon.username),
            getConfigListEntry(_("Password"), config.plugins.fritzmon.password),
            getConfigListEntry(_("Show inactive devices"), config.plugins.fritzmon.show_inactive),
        ]
        ConfigListScreen.__init__(self, self._entries, session=session)

        try:
            self["config"].onSelectionChanged.append(self._update_hint)
        except Exception:
            pass
        self._update_hint()

        self["actions"] = ActionMap(
            ["SetupActions", "ColorActions", "OkCancelActions", "WizardActions"],
            {
                "save": self.key_green,
                "cancel": self.key_red,
                "green": self.key_green,
                "red": self.key_red,
                "yellow": self.key_yellow,
                "ok": self.key_ok,
                "back": self.key_red,
            },
            -2,
        )

    # ------------------------------------------------------------------
    # Key handlers
    # ------------------------------------------------------------------

    def key_ok(self):
        current = self["config"].getCurrent()
        if current and Input is not None and InputBox is not None:
            cfg_item = current[1]
            if cfg_item is config.plugins.fritzmon.host:
                self.session.openWithCallback(
                    lambda v: self._on_text_input(v, config.plugins.fritzmon.host),
                    InputBox,
                    title=_("Fritz!Box Host/IP"),
                    text=config.plugins.fritzmon.host.value or "",
                    maxSize=64,
                    type=Input.TEXT,
                )
                return
            if cfg_item is config.plugins.fritzmon.username:
                self.session.openWithCallback(
                    lambda v: self._on_text_input(v, config.plugins.fritzmon.username),
                    InputBox,
                    title=_("Username"),
                    text=config.plugins.fritzmon.username.value or "",
                    maxSize=64,
                    type=Input.TEXT,
                )
                return
            if cfg_item is config.plugins.fritzmon.password:
                self.session.openWithCallback(
                    lambda v: self._on_text_input(v, config.plugins.fritzmon.password),
                    InputBox,
                    title=_("Password"),
                    text=config.plugins.fritzmon.password.value or "",
                    maxSize=64,
                    type=Input.TEXT,
                )
                return
            if cfg_item is config.plugins.fritzmon.port:
                self.session.openWithCallback(
                    self._on_port_input,
                    InputBox,
                    title=_("Port"),
                    text=str(config.plugins.fritzmon.port.value or "49000"),
                    maxSize=5,
                    type=Input.NUMBER,
                )
                return
        try:
            ConfigListScreen.keyOK(self)
        except Exception:
            pass

    def key_green(self):
        host = (config.plugins.fritzmon.host.value or "").strip()
        if not host:
            self.session.open(
                MessageBox,
                _("Please configure the Fritz!Box connection first"),
                MessageBox.TYPE_ERROR,
                timeout=5,
            )
            return

        for entry in self["config"].list:
            entry[1].save()
        config.plugins.fritzmon.save()
        try:
            configfile.save()
        except Exception:
            pass

        self.session.open(
            MessageBox, _("Settings saved"), MessageBox.TYPE_INFO, timeout=3
        )

        if self.open_main_on_save:
            from .plugin import get_app
            self.session.open(FritzMonMainScreen, get_app())
        self.close()

    def key_red(self):
        for entry in self["config"].list:
            try:
                entry[1].cancel()
            except Exception:
                pass
        self.close()

    def key_yellow(self):
        """Test the connection using current (unsaved) field values."""
        host = (config.plugins.fritzmon.host.value or "").strip()
        port = 49000
        try:
            port = int(config.plugins.fritzmon.port.value or 49000)
        except Exception:
            pass
        username = (config.plugins.fritzmon.username.value or "").strip()
        password = (config.plugins.fritzmon.password.value or "").strip()

        from .core.api import FritzMonApiClient
        client = FritzMonApiClient(host=host, port=port, username=username, password=password)
        ok, error = client.ping()
        if ok:
            self.session.open(
                MessageBox,
                _("Connection test successful"),
                MessageBox.TYPE_INFO,
                timeout=4,
            )
        else:
            self.session.open(
                MessageBox,
                _("Connection test failed") + ":\n" + str(error),
                MessageBox.TYPE_ERROR,
                timeout=6,
            )

    # ------------------------------------------------------------------
    # Input callbacks
    # ------------------------------------------------------------------

    def _on_text_input(self, value, cfg_entry):
        if value is None:
            return
        cfg_entry.value = str(value).strip()

    def _on_port_input(self, value=None):
        if value is None:
            return
        digits = "".join(ch for ch in str(value) if ch.isdigit())
        if not digits:
            return
        try:
            config.plugins.fritzmon.port.value = int(digits)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Help text
    # ------------------------------------------------------------------

    def _update_hint(self):
        current = self["config"].getCurrent()
        if not current:
            return
        item = current[1]
        key = None
        if item is config.plugins.fritzmon.host:
            key = "host"
        elif item is config.plugins.fritzmon.port:
            key = "port"
        elif item is config.plugins.fritzmon.username:
            key = "username"
        elif item is config.plugins.fritzmon.password:
            key = "password"
        elif item is config.plugins.fritzmon.show_inactive:
            key = "show_inactive"
        if key:
            self["hint"].setText(_(self._HELP[key]))


# ===========================================================================
# Info / About screen
# ===========================================================================

class FritzMonInfoScreen(Screen):
    skin = """
        <screen name="FritzMonInfoScreen" position="center,90" size="1000,620" title="FritzMon Info">
            <widget source="title" render="Label" position="20,10" size="960,40" font="Regular;34" />
            <widget name="body" position="20,60" size="680,500" font="Regular;24" scrollbarMode="showOnDemand" />
            <widget name="qr" position="720,100" size="240,240" alphatest="blend" />
            <widget source="support" render="Label" position="20,568" size="960,24" font="Regular;20" foregroundColor="#666666" />
            <ePixmap pixmap="skin_default/buttons/red.png" position="20,590" size="220,30" alphatest="on" />
            <widget source="key_red" render="Label" position="20,590" size="220,30" font="Regular;24" halign="center" valign="center" transparent="1" />
        </screen>
    """

    def __init__(self, session):
        Screen.__init__(self, session)
        self["title"] = StaticText(_("FritzMon Information"))
        self["key_red"] = StaticText(_("Close"))
        self["support"] = StaticText(SUPPORT_LINE)
        self["body"] = ScrollLabel(self._build_text())
        self["qr"] = Pixmap()

        self["actions"] = ActionMap(
            ["OkCancelActions", "ColorActions", "DirectionActions"],
            {
                "ok": self.close,
                "cancel": self.close,
                "red": self.close,
                "up": self["body"].pageUp,
                "down": self["body"].pageDown,
                "left": self["body"].pageUp,
                "right": self["body"].pageDown,
            },
            -1,
        )

        self.onLayoutFinish.append(self._load_qr)

    def _build_text(self):
        lines = [
            "FritzMon v1.0",
            "",
            _("Data source") + ": AVM TR-064 (Fritz!Box SOAP API)",
            "Port: 49000 (unverschlüsselt)",
            "",
            "Zeigt alle im Fritz!Box-Netzwerk bekannten Geräte:",
            "  \u2022 Hostname, IP-Adresse, MAC-Adresse",
            "  \u2022 Verbindungstyp (WLAN / Ethernet)",
            "  \u2022 Aktueller Online-Status",
            "  \u2022 Adressquelle (DHCP / Statisch)",
            "",
            "Navigation:",
            "  OK         \u2192 Gerätedetails",
            "  Links/Rechts \u2192 Filter umschalten",
            "  Grün       \u2192 Aktualisieren",
            "  Gelb       \u2192 Einstellungen",
            "  Blau       \u2192 Diese Info-Seite",
            "",
            "Buy me a coffee: https://buymeacoffee.com/madoe21",
            "GitHub: https://github.com/madoe21/enigma2-fritzmon",
        ]
        return "\n".join(lines)

    def _load_qr(self):
        candidates = [
            resolveFilename(SCOPE_PLUGINS, "Extensions/fritz_mon/res/qr_buymeacoffee.png"),
            os.path.join(os.path.dirname(__file__), "res", "qr_buymeacoffee.png"),
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    self["qr"].instance.setPixmapFromFile(path)
                    return
                except Exception:
                    pass
