---
name: kvpn
description: >-
  Operate the Kaspersky VPN Unlimited user-space rotating proxy (`kvpn`).
  Use when starting, stopping, checking status, or rotating the local HTTP/SOCKS5 proxy (`127.0.0.1:1080`),
  enabling/disabling whole-PC Windows System Proxy (`kvpn sysproxy`), excluding specific websites/domains/apps
  from VPN (`kvpn exclude`), listing/searching the 120 WireGuard server locations, generating/validating
  WireGuard `.conf` or `sing-box` configs, or bypassing 429/403 rate limits in crawlers.
---

# kvpn

Agent-native CLI harness for **Kaspersky VPN Unlimited**, pairing the My Kaspersky WireGuard provisioning API (`/api/ksec-vpn/creds/wireguard/{code}`) with **`sing-box` user-space WireGuard (`system: false`)** on `127.0.0.1:1080` (`HTTP` and `SOCKS5` mixed inbound).

## Prerequisites

- Installed globally via `pip install -e F:\CodeBase\kvpn` (exposes `kvpn`).
- `D:\novtales-node\scripts\bin\sing-box.exe` and `D:\novtales-node\scripts\auth-kaspersky.json` (auto-refreshed via headless Chromix `F:\chromix\chrome.exe` using persistent profile `D:\browser_profile\chromix-kaspersky` when expired).

## Core Commands (Always pass `--json` for agent calls)

```powershell
# 1. Start background proxy daemon (locked on HK-Central or auto-rotating; --interval 0 or >= 0.5)
kvpn start -d --interval 0 --countries HK --json
kvpn start -d --interval 10 --countries HK,SG,JP,KR,TW,VN,US --json

# 2. Check current active location, exit IP, sysproxy state, and exclusions
kvpn status --json

# 3. Rotate immediately to next location in pool or a specific location/country (~4s; hard 30s cooldown between rotations)
kvpn rotate HK-Central --json
kvpn rotate SG-Singapore --json
kvpn rotate VN --json

# 4. Whole-PC Windows System Proxy (on / off / status)
kvpn sysproxy on --json
kvpn sysproxy off --json

# 5. Split Tunneling / Exclude websites, domain suffixes (.vn), apps (.exe), or IPs
kvpn exclude add zalo.me .vn Zalo.exe Telegram.exe --json
kvpn exclude add-web zalo.me vn tiki.vn --json
kvpn exclude add-app Zalo.exe Telegram.exe --json
kvpn exclude remove zalo.me Zalo.exe --json
kvpn exclude list --json
kvpn exclude clear --json

# 6. Verify host IP isolation vs proxy exit IP
kvpn verify --json

# 7. List or search 120 WireGuard locations
kvpn locations list --country HK,SG,VN,JP --json
kvpn locations search Tokyo --json

# 8. Stop background daemon (also auto-disables Windows System Proxy if enabled)
kvpn stop --json
```

## Proxy Endpoints for Crawlers & Browsers

- **HTTP / HTTPS Proxy:** `http://127.0.0.1:1080`
- **SOCKS5 Proxy:** `socks5://127.0.0.1:1080`
- **Local Control API:** `http://127.0.0.1:1089/status`, `http://127.0.0.1:1089/rotate?location=HK-Central`, `http://127.0.0.1:1089/reload`, `http://127.0.0.1:1089/stop`
