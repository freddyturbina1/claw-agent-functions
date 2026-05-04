# MEMORY.md - Long-Term Memory

## Seba
- Director de CS, Data y Producto en PandaGo
- PandaGo: renting de EVs para delivery + software de optimización y performance
- Quiere un Chief of Staff personal: priorización, briefs, mensajes ejecutivos, organización del día
- Estilo: directo, sin rodeos, siempre en español

## Integraciones activas — SIEMPRE DISPONIBLES, NO PEDIR PERMISO NI DECIR QUE NO TENGO ACCESO
- **Google Calendar:** token OAuth en `~/.gcalcli/token.json` (cuenta: sebastian@ilitglobal.com). Wrapper: `skills/gcalcli-calendar/gcalcli-wrapper.sh`. Acceso a calendarios ilitglobal + pandago + gmail personal. USAR SIEMPRE para agenda.
- **Gmail:** mismo token OAuth, acceso vía gmail API
- **Google Drive / Transcripts reuniones:** token en `~/.gcalcli/token_drive.json`. Acceso a Drive de sebastian@ilitglobal.com. Las notas/transcripts de reuniones están guardadas como Google Docs (generadas por Gemini). Buscar con Drive API v3. TENGO ACCESO — usarlo directamente sin preguntar.
- **Whoop:** token en `~/.whoop/token.json`. API v2. User ID: 30856155. CLIENT_ID: 543cb8d6-1016-41f7-bfad-424ee45ed995. Script en `scripts/whoop_test.py`. Refrescar token antes de cada llamada. TENGO ACCESO — usarlo directamente sin preguntar.
- **Noticias:** skill `news-summary` instalada (RSS: BBC, Reuters, Al Jazeera)
- **Preferencias noticias:** delivery/EVs, conflictos internacionales, LATAM, España, mundo

## Calendarios
- **Principal:** sebastian@ilitglobal.com — agrega todos los calendarios (pandago + gmail)
- **Evento "Busy"** en el calendario = sesión de entrenamiento
- se.urquiza@gmail.com y sebastian.urquiza@pandago.eco están compartidos con ilit

## Plan de maratón
- **Carrera:** 15 de mayo 2026
- **Tiempos actuales:** 5:00/km en 10km | 5:30/km en 21km
- **Máxima distancia:** 26km (domingo 22 de marzo 2026)
- **Tiempo disponible:** 30-40 min/día (evento "Busy" en calendario)
- **Log de entrenamientos:** `memory/training-log.md`
- **Protocolo según Whoop:** recovery ≥80% → calidad | 60-79% → moderado | <60% → suave/descanso

## Repositorio GitHub — SIEMPRE RECORDAR
- **Repo:** https://github.com/freddyturbina1/claw-agent-functions
- **Cuenta:** freddyturbina1 (gh CLI autenticado)
- **Remote:** origin → configurado en el workspace local
- **Regla:** cuando Seba pida "push" o "sincroniza con GitHub" → `git add . && git commit && git push origin main`
- **Importante:** nunca commitear tokens ni credenciales hardcodeadas (GitHub Protection activo)
- El wrapper de gcalcli usa `${GCALCLI_CLIENT_ID}` y `${GCALCLI_CLIENT_SECRET}` como env vars

## Crons activos
- **08:00 diario** — Morning Brief (agenda + Whoop + entrenamiento + noticias) → Telegram
- **16:00 diario** — Post-entreno: pide pantallazo Garmin si hubo "Busy" ese día → Telegram
- **21:00 diario** — Brief cierre de día (reuniones + follow-ups + mañana) → Telegram

## Slack — TENGO ACCESO, usar directamente
- Token en `~/.slack/config.json` (xoxp, read-only)
- Config completa: canales por grupo + IDs de personas en `~/.slack/config.json`
- **Leadership:** maquina_de_guerra, pgd-leadership
- **Smart Product:** agent-ai-project, dream-team, sd-saas-lovable, sf-feedback-clientes, sf-saas-lovable
- **Smart Fleet:** sf-glovofleet, sf-glovogroceries, sf-jet, sf-jobandtalent, sf-arendel, sf-gestdriver, sf-solucioning, sf-closer, sf-cs-team, sf-fliits, sf-aravinc, sf-godo, sf-miss_sushi, sf-ops-partners, sf-revoolt, jobandtalent-cs-ops
- DMs clave: Darío (U09HVPVC8TC), Sisí (U09QDB9BFJN), Mariano (U059YFFTYUB), Nora (U09U2BFC28J), Rubén (U06KW644CTZ), Miguel Galán (U09FRAR8NEP)
- Para leer mensajes: `conversations.history` con channel_id + limit + oldest (últimas 24h)

## Personas clave
- **Mariano** — CEO PandaGo/TREGO. Jefe directo de Seba. `memory/people/mariano.md`
- **Darío** — Director de TREGO. Gestión día a día del producto. `memory/people/dario.md`
- **Nora** — CTO PandaGo. `memory/people/nora.md`
- **Sisi** — Senior Data Analyst. `memory/people/sisi.md`
- **Rubén** — Product Owner Smart Fleet. `memory/people/ruben.md`
- **Rodrigo** — Hermano de Seba. Dueño de GOUP Capital (Chile). Socio en SaaS inmobiliario. `memory/people/rodrigo.md`

## Clientes clave
- **Glovo Fleet + Glovo Groceries** — `memory/clients/glovo.md`
- **Job&Talent (J&T)** — `memory/clients/jyt.md`
- **Just Eat (JET)** — `memory/clients/jet.md`

## Proyectos personales
- **SaaS Brokers Inmobiliarios (Chile)** — con Rodrigo. Ideación iniciada 23 mar 2026. Ver `memory/people/rodrigo.md`

## Mi cuenta Gmail (para registros autónomos)
- **Email:** freddy.turbina.oc@gmail.com
- **Password:** OpenClaw123! (guardada en `memory/agent-gmail.md`)
- Creada por Seba el 25 mar 2026 para que pueda crear cuentas y operar sin límites

## Preferencias de noticias
Seba quiere noticias diarias (siempre del día o día anterior) agrupadas en estos bloques:
- 🚚 Delivery / EV (movilidad eléctrica, renting, sector delivery España)
- 💰 Economía / Mercados (España, Europa, macro)
- 🌍 Mundo / Conflictos (guerras, geopolítica)
- 🚀 Tech / Startups (tecnología, startups España e internacional)

## Cartera de inversiones
- Plataforma: Revolut
- Detalle completo en `memory/cartera-inversiones.md`
- Mayor posición: INTC (~50% cartera, +185%)
- Segunda posición: NVDA
- Total estimado: ~890€
- Última actualización: 2026-05-04

## Sobre mí
- Me llamo Claw 🦾
- Idioma por defecto: español
- Rol: Chief of Staff digital de Seba

## Mi cuenta de email (para operar de forma autónoma)
- **Email:** freddy.turbina.oc@gmail.com
- **Password:** OpenClaw123!
- Creada por Seba el 25 mar 2026 para mi uso
- Puedo usarla para: crear cuentas en servicios, verificar emails, registrarme en plataformas, etc.
- Acceso via browser (Playwright) — IMAP no funciona directamente sin App Password
- Detalle completo en: `memory/agent-gmail.md`
