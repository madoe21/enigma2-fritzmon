# -*- coding: utf-8 -*-
from __future__ import absolute_import

import gettext

from Components.Language import language
from Tools.Directories import SCOPE_PLUGINS, resolveFilename

PLUGIN_DOMAIN = "fritz_mon"
PLUGIN_PATH = "Extensions/fritz_mon/locale"

_DE_FALLBACK = {
    # General
    "Close": "Schließen",
    "Cancel": "Abbrechen",
    "Save": "Speichern",
    "Refresh": "Aktualisieren",
    "Settings": "Einstellungen",
    "Information": "Information",
    "Back": "Zurück",
    "Main menu": "Hauptmenü",
    "Error": "Fehler",
    "Loading...": "Wird geladen...",
    "Settings saved": "Einstellungen gespeichert",
    "Please configure the Fritz!Box connection first": "Bitte zuerst die Fritz!Box-Verbindung konfigurieren",
    "Using cached data": "Nutze zwischengespeicherte Daten",
    # Main screen
    "FritzMon - Network Overview": "FritzMon – Netzwerkübersicht",
    "Devices": "Geräte",
    "Active only": "Nur aktive",
    "All devices": "Alle Geräte",
    "Filter": "Filter",
    "Updated": "Stand",
    "No devices found": "Keine Geräte gefunden",
    "Hostname": "Hostname",
    "IP Address": "IP-Adresse",
    "Connection": "Verbindung",
    "Status": "Status",
    "active": "aktiv",
    "inactive": "inaktiv",
    "WiFi": "WLAN",
    "Ethernet": "Kabel",
    "unknown": "unbekannt",
    # Detail screen
    "Device Details": "Gerätedetails",
    "MAC Address": "MAC-Adresse",
    "Address Source": "Adressquelle",
    "Interface Type": "Schnittstellentyp",
    "n/a": "k.A.",
    # Settings screen
    "Fritz!Box Settings": "Fritz!Box-Einstellungen",
    "Fritz!Box Host/IP": "Fritz!Box Host/IP",
    "Port": "Port",
    "Username": "Benutzername",
    "Password": "Passwort",
    "Show inactive devices": "Inaktive Geräte anzeigen",
    "Enter Fritz!Box hostname or IP address": "Hostname oder IP-Adresse der Fritz!Box eingeben",
    "Enter the TR-064 port (default: 49000)": "TR-064-Port eingeben (Standard: 49000)",
    "Enter Fritz!Box username (leave empty if none)": "Fritz!Box-Benutzername (leer lassen wenn keiner gesetzt)",
    "Enter Fritz!Box password": "Fritz!Box-Passwort eingeben",
    "Show all known devices (active and inactive)": "Alle bekannten Geräte anzeigen (aktive und inaktive)",
    "Connection test successful": "Verbindungstest erfolgreich",
    "Connection test failed": "Verbindungstest fehlgeschlagen",
    "Test connection": "Verbindung testen",
    # Info screen
    "FritzMon Information": "FritzMon Information",
    "Data source": "Datenquelle",
}


def localeInit():
    gettext.bindtextdomain(PLUGIN_DOMAIN, resolveFilename(SCOPE_PLUGINS, PLUGIN_PATH))
    try:
        gettext.bind_textdomain_codeset(PLUGIN_DOMAIN, "UTF-8")
    except Exception:
        pass


def _(txt):
    translated = gettext.dgettext(PLUGIN_DOMAIN, txt)
    if translated != txt:
        return translated

    try:
        lang = language.getLanguage()[:2]
    except Exception:
        lang = "en"

    if lang == "de":
        return _DE_FALLBACK.get(txt, txt)
    return txt


localeInit()
try:
    language.addCallback(localeInit)
except Exception:
    pass
