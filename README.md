# FritzMon – Enigma2 Plugin

Fritz!Box Network Monitor plugin for Enigma2. Shows all devices on the
Fritz!Box network with IP address, MAC address, connection type (LAN/WLAN)
and online/offline status. Uses the TR-064 SOAP API.

---

## Features

| Button | Action |
|--------|--------|
| **Red** | Close / Back |
| **Green** | Refresh device list |
| **Yellow** | Open Settings |
| **Blue** | Open Information screen |
| **OK** | View device details |

### Device list
- All active and known network devices
- Hostname, IP address, MAC address
- Connection type: LAN / WLAN 2.4 GHz / WLAN 5 GHz / Guest
- Online/offline status with last-seen timestamp

---

## Requirements

- AVM Fritz!Box with TR-064 enabled (UPnP + allow access for applications)
- Fritz!Box user account with read access

---

## Build & deploy

```bash
# 1. Copy .env.example to .env and enter your box credentials
cp .env.example .env

# 2. Build the .ipk package
make build

# 3. Build, upload and install on the box (also pushes Fritz!Box credentials)
make install

# 4. Restart Enigma2
make restart

# 5. Or do all three steps at once
make deploy
```

The package is placed in `build/enigma2-plugin-extensions-fritzmon_1.0.0_all.ipk`.

---

## Settings / .env variables

| Variable | Description |
|----------|-------------|
| `BOX_HOST` | Enigma2 box IP or hostname |
| `BOX_USER` | SSH user (usually `root`) |
| `BOX_PORT` | SSH port (default `22`) |
| `FRITZ_HOST` | Fritz!Box hostname (default `fritz.box`) |
| `FRITZ_PORT` | Fritz!Box TR-064 port (default `49000`) |
| `FRITZ_USER` | Fritz!Box user |
| `FRITZ_PASSWORD` | Fritz!Box password |

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🤝 Contributing

Found a bug or have a suggestion for improvement? Please create an issue or pull request.

I appreciate everyone who supports me and the project! For any requests and suggestions, feel free to provide feedback.

<p>
  <a href="https://www.buymeacoffee.com/madoe21">
    <img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" height="50" alt="Buy Me a Coffee">
  </a>

  <a href="https://ko-fi.com/madoe21">
    <img src="https://storage.ko-fi.com/cdn/kofi3.png?v=3" height="50" alt="Ko-fi">
  </a>

  <a href="https://paypal.me/MartinD809">
    <img src="https://www.paypalobjects.com/webstatic/mktg/logo/pp_cc_mark_111x69.jpg" height="50" alt="PayPal">
  </a>
</p>

---

## Built with aiflow

This project was built with support from **[aiflow](https://cyber93de.github.io/aiflow/)** — *built with aiflow*.
