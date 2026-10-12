\# WAN Deployment Baseline



Branch:

feature/wan-deployment



Baseline test:

pytest -v



Result:

355 passed in 15.04s



Status:

All original project tests passed before WAN-related changes.



Environment:

Windows

Python 3.14.0



\## WAN Manual Verification



Tunnel URL:

https://alt-grid-elephant-roller.trycloudflare.com



Server config:

ALLOWED\_ORIGINS=https://alt-grid-elephant-roller.trycloudflare.com

COOKIE\_SECURE=true

ADMIN\_USERNAME=admin

ADMIN\_PASSWORD=<configured via environment variable>



Manual checks:

\- Desktop WAN URL access: PASS

\- Mobile 4G/5G WAN URL access: PASS

\- Admin login over HTTPS: PASS

\- Profile page over HTTPS: PASS

\- Admin page over HTTPS: PASS

\- Tournament settings update over HTTPS: PASS

\- FFA portal force open: PASS

\- Bot upload over HTTPS: PASS

\- Boss deployment over HTTPS: PASS

\- Challenge creation over HTTPS: PASS

\- Replay page over HTTPS: PASS



Observed logs:

\- POST /api/admin/settings -> 200 OK

\- POST /api/admin/bosses/deploy -> 200 OK

\- POST /api/matches/challenge -> 201 Created

\- GET /replay/1 -> 200 OK

\- GET /api/matches/1/replay -> 200 OK

\- 304 Not Modified appeared only for cached static assets and is expected behavior.



Notes:

Quick Tunnel URL is temporary and may change after restarting cloudflared.



\## Environment Modes for WAN Demo and Testing



This project uses environment variables to switch between local testing mode and WAN HTTPS demo mode.



\### WAN HTTPS Demo Mode



Use this mode only when exposing the application through Cloudflare Tunnel or another HTTPS public endpoint.



Example:



ALLOWED\_ORIGINS=https://<your-tunnel>.trycloudflare.com

COOKIE\_SECURE=true

ADMIN\_USERNAME=admin

ADMIN\_PASSWORD=<strong-demo-password>



Run:



python main.py



Notes:

\- Do not commit real passwords into the repository.

\- Quick Tunnel URLs are temporary and may change after restarting cloudflared.

\- If the tunnel URL changes, ALLOWED\_ORIGINS must be updated to the new HTTPS URL.



\### Local Pytest Mode



Before running pytest, clear WAN-specific environment variables so tests use the default local credentials and settings.



PowerShell:



Remove-Item Env:ADMIN\_PASSWORD -ErrorAction SilentlyContinue

Remove-Item Env:ADMIN\_USERNAME -ErrorAction SilentlyContinue

Remove-Item Env:COOKIE\_SECURE -ErrorAction SilentlyContinue

Remove-Item Env:ALLOWED\_ORIGINS -ErrorAction SilentlyContinue



Then run:



pytest -v



Reason:

The default test suite expects the seeded admin account to use the default local password admin123. If ADMIN\_PASSWORD remains set from WAN demo mode, admin login tests may fail with 401 Unauthorized even though the application code is correct.

