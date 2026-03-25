# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

## Google Calendar (gcalcli)

- **Wrapper:** `skills/gcalcli-calendar/gcalcli-wrapper.sh`
- **Config:** `~/.gcalcli/` (credenciales OAuth en pickle `oauth`)
- **Calendarios:** sebastian@ilitglobal.com (principal), se.urquiza@gmail.com
- **Uso:** `bash skills/gcalcli-calendar/gcalcli-wrapper.sh --nocolor agenda today +7d`
- **Token:** tiene refresh_token, no caduca manualmente

## Google Gmail

- **Auth:** mismo token OAuth en `~/.gcalcli/token.json` (scopes: gmail.readonly + gmail.modify)
- **Acceso vía:** Python google-api-python-client (gmail API v1)

Add whatever helps you do your job. This is your cheat sheet.
