# Proxy Setup Guide

## Why Use a Proxy?

1. **Hide your IP address** - Protect your identity
2. **Bypass regional restrictions** - Access content from other countries
3. **Reduce ban risk** - Use different IPs for different accounts
4. **Target specific regions** - Use Japan IP for Japanese audience

---

## Using the Proxy Feature

### Basic Usage

```cmd
python -m outreach_bot.main --sheet "YOUR_SHEET_URL" --dm --proxy "http://host:port"
```

### Proxy Formats Supported

```
# HTTP Proxy (most common)
--proxy "http://123.45.67.89:8080"

# HTTPS Proxy
--proxy "https://123.45.67.89:8080"

# SOCKS5 Proxy
--proxy "socks5://123.45.67.89:1080"

# Proxy with authentication
--proxy "http://username:password@host:port"
```

---

## Getting Japan IP Proxies

### Option 1: Paid Proxy Services (Recommended)

**Best for reliability and speed:**

| Service | Price | Features |
|---------|-------|----------|
| [Bright Data](https://brightdata.com) | ~$15/GB | Residential IPs, Japan available |
| [Smartproxy](https://smartproxy.com) | ~$12/GB | Japan residential proxies |
| [Oxylabs](https://oxylabs.io) | ~$15/GB | Premium Japan IPs |
| [IPRoyal](https://iproyal.com) | ~$7/GB | Budget option, Japan available |
| [Webshare](https://webshare.io) | Free tier + paid | 10 free proxies |

**How to use:**
1. Sign up for service
2. Select Japan location
3. Get proxy credentials (host:port:user:pass)
4. Use: `--proxy "http://user:pass@host:port"`

### Option 2: VPN with SOCKS5

Some VPNs provide SOCKS5 proxy access:

- **NordVPN** - SOCKS5 with Japan servers
- **PIA (Private Internet Access)** - SOCKS5 support
- **Mullvad** - SOCKS5 proxy

### Option 3: Free Proxies (Not Recommended)

Free proxies are:
- Often slow and unreliable
- May log your data
- Get banned quickly

If you must use free proxies:
- https://free-proxy-list.net/
- https://www.sslproxies.org/
- Filter by country: Japan (JP)

---

## Testing Your Proxy

### Check your current IP:

```cmd
# Without proxy
curl https://api.ipify.org

# With proxy
curl --proxy "http://host:port" https://api.ipify.org
```

### Check IP location:

Visit https://whatismyipaddress.com/ in the browser opened by the bot.

---

## Japanese Message Templates

When reaching out to Japanese users, use the `--category japanese` flag:

```cmd
python -m outreach_bot.main --sheet "URL" --dm --category japanese --proxy "http://japan-proxy:port"
```

### Available Japanese Categories:

| Category | Description |
|----------|-------------|
| `japanese` | Full recruitment message in Japanese |
| `jp_short` | Shorter version |
| `jp_intro` | Brief introduction |

---

## Example Commands

### Japanese Outreach (with Japan proxy)

```cmd
python -m outreach_bot.main ^
    --sheet "YOUR_SHEET_URL" ^
    --dm ^
    --category japanese ^
    --proxy "http://user:pass@jp-proxy.example.com:8080" ^
    --max-targets 10
```

### Thai Outreach (no proxy needed)

```cmd
python -m outreach_bot.main ^
    --sheet "YOUR_SHEET_URL" ^
    --dm ^
    --max-targets 10
```

---

## Important Notes

1. **Instagram may still detect proxy use** - Use residential proxies when possible
2. **Proxy slows down browsing** - Allow more time between actions
3. **Login may be required again** - Instagram often asks for re-login with new IP
4. **Test before bulk sending** - Verify proxy works with 1-2 DMs first

---

## Troubleshooting

### "Connection refused"
- Check proxy is online
- Verify host:port is correct
- Try different proxy

### "Proxy authentication required"
- Include username:password in proxy URL
- Format: `http://user:pass@host:port`

### "Instagram says suspicious login"
- Normal when changing IP
- Complete verification
- Wait a few hours before bulk sending

### "Proxy too slow"
- Use paid residential proxies
- Check proxy speed before using
- Consider closer geographic location
