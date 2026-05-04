# 📊 Market Analyst Agent

Agente de análisis de mercados financieros integrado con OpenClaw. Monitorea noticias en tiempo real, analiza el impacto en cartera y genera recomendaciones accionables vía Telegram.

---

## ¿Cómo funciona?

### Flujo general

```
cartera-inversiones.md  ──→  portfolio.json  ──→  market_analyst.py  ──→  Análisis LLM  ──→  Telegram
     (fuente de verdad)          (sync auto)         (noticias RSS)         (OpenClaw)
```

1. **Sincronización de cartera:** Antes de cada análisis, el agente lee `memory/cartera-inversiones.md` (fuente de verdad) y actualiza `portfolio.json` automáticamente. Tú nunca tocas `portfolio.json` directamente.

2. **Recolección de noticias:** `market_analyst.py` hace scraping de ~20 feeds RSS financieros (Yahoo Finance, Reuters, CNBC, Bloomberg, MarketWatch, FT, etc.) + NewsAPI + Brave Search. Devuelve un JSON con todos los titulares.

3. **Análisis LLM:** El cron de OpenClaw recibe los titulares y los analiza con Claude como trader experto. Genera recomendaciones con catalizador concreto, mecánica de precio, riesgo e impacto en tu cartera.

4. **Entrega:** El resultado se envía a Telegram. Las recomendaciones se guardan en `last_recommendations.json` para mantener coherencia entre ejecuciones.

---

## Cuándo se dispara

| Cron | Horario | Propósito |
|------|---------|-----------|
| 🇪🇺 Pre-apertura EU | 8:30 L-V | 30 min antes de que abran Europa |
| 🇺🇸 Pre-apertura NY | 15:00 L-V | 30 min antes de que abra NYSE/Nasdaq |
| 🔔 Pre-cierre NY | 21:30 L-V | 30 min antes del cierre de NYSE |
| ⚡ Evento-driven | Cada 20 min, 9:00–21:00 L-V | Solo envía si hay catalizador de alto impacto |

### Criterios de "alto impacto" (evento-driven)
El agente solo envía alerta si detecta AL MENOS UNO de estos:
- Índice principal (S&P 500, Nasdaq, DAX) mueve >1.5% en la última hora
- Una acción de tu cartera mueve >3% sin causa conocida previa
- Dato macro sorpresa: CPI, Fed, BCE, empleo, PIB
- Escalada geopolítica nueva (ataque, sanciones, colapso negociación)
- OPA/M&A anunciada en las últimas 2 horas
- Earnings sorpresa >10%
- Aprobación/rechazo FDA inesperado
- Crypto move >5% en 1 hora
- Quiebra o colapso de empresa/banco relevante

---

## Archivos

```
skills/market-analyst/
├── market_analyst.py          # Script de recolección de noticias (RSS + APIs)
├── portfolio.json             # Cartera actual (se sincroniza desde cartera-inversiones.md)
├── last_recommendations.json  # Últimas recomendaciones (para coherencia entre ejecuciones)
├── state.json                 # Cache de artículos vistos (evita repetición)
├── config.json                # API keys (NewsAPI, Brave) — NO incluido en git
├── run_analysis.sh            # Script auxiliar
└── README.md                  # Este archivo

memory/
└── cartera-inversiones.md     # Fuente de verdad de la cartera (Revolut)
```

---

## Cómo actualizar la cartera

Simplemente edita `memory/cartera-inversiones.md` con los valores actuales de Revolut. El agente sincronizará `portfolio.json` automáticamente en la próxima ejecución.

Formato esperado en `cartera-inversiones.md`:
```markdown
| Ticker | Empresa | Valor (€) | % P&L |
|--------|---------|-----------|-------|
| NVDA   | Nvidia  | 302.80    | +2.33% |
```

---

## Formato de salida en Telegram

**Análisis programado (3x/día):**
```
📊 MARKET PULSE — Pre-apertura EU 🇪🇺 08:30 CET

🟢 COMPRAR / 🔴 VENDER / 👁 VIGILAR [NOMBRE] ([TICKER])
→ Qué pasó: [noticia concreta]
→ Por qué mueve el precio: [mecánica]
→ Riesgo: [qué puede salir mal]
→ 📌 En tu cartera: [impacto directo si aplica]

💡 Concepto del día: [1 concepto de inversión, 2 líneas]
🌍 Macro en 1 línea: [factor global más importante]
```

**Alerta evento-driven:**
```
⚡ ALERTA MERCADO — [evento en 5 palabras] — [hora] CET

🚨 Qué pasó: [descripción concreta]
📊 Por qué importa: [mecánica del impacto]
🎯 Acción recomendada: [🟢/🔴/👁] [TICKER]
📌 Tu cartera: [impacto directo o "No afecta directamente"]
⚠️ Riesgo: [qué puede salir mal]
```

---

## Requisitos

- Python 3.x (sin dependencias externas — solo stdlib)
- OpenClaw con cron habilitado
- Token de Telegram configurado en OpenClaw
- (Opcional) API key de NewsAPI y Brave Search en `config.json`

---

## config.json (no incluido en git)

Crea el archivo con esta estructura:
```json
{
  "newsapi_key": "TU_KEY",
  "brave_key": "TU_KEY",
  "telegram_enabled": true
}
```

Obtén tu key gratuita en: https://newsapi.org
