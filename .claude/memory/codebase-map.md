# Codebase map (onboarding 2026-07-08)

**enigma2-fritzmon** — Enigma2 (OpenATV 7.6) plugin: FRITZ!Box monitor
(connection/throughput/status) on the TV. Python.

## Layout
- `src/fritz_mon/plugin.py` (~238 LOC) — entry.
- `src/fritz_mon/api.py` (~178) — TR-064 **SOAP** client (`_soap_call`,
  `Request` + `opener.open(req, timeout=10)`). **Data layer.**
- `src/fritz_mon/screens.py` (~778) — enigma2 GUI.
- `res/`, `control/`, `build/` (gitignored ipk).

## Conventions
- Enigma2 Py3. `api.py` correctly sets a 10s timeout on the SOAP call — keep
  that pattern for any new request.
- Twisted/enigma2 GUI on the main thread; long calls must not block it.

## Kodi portability: **monolithic (data layer already separate)**
3 files import enigma2 (screens/plugin). `api.py` is a self-contained SOAP
client. Port = move `api.py` to `core/` (verify enigma2-free), add
`platform/kodi/`. Target shape: lotto/stocks/weather (core/-split).
