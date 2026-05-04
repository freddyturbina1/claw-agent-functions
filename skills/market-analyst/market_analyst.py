#!/usr/bin/env python3
"""
Market Analyst Agent
Fetches news from multiple sources, analyzes market impact, and generates
buy/sell/hold recommendations for stocks.
"""

import os
import json
import sys
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
import urllib.request
import urllib.parse
import urllib.error

# ── Config ──────────────────────────────────────────────────────────────────
WORKSPACE = Path.home() / ".openclaw/workspace"
CONFIG_FILE = WORKSPACE / "skills/market-analyst/config.json"
STATE_FILE = WORKSPACE / "skills/market-analyst/state.json"

# Portfolio to prioritize
PORTFOLIO = ["NVIDIA", "NVDA", "Netflix", "NFLX", "Google", "GOOGL", "GOOG", "Iberdrola", "IBE"]

# Key tickers + sectors to watch
WATCHLIST = {
    "Tech": ["NVDA", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA", "AMD", "INTC", "ASML"],
    "Energy": ["XOM", "CVX", "BP", "SHEL", "IBE.MC", "REP.MC", "NEE", "ENPH"],
    "Finance": ["JPM", "GS", "BAC", "BRK", "SAN.MC", "BBVA.MC"],
    "Defense": ["LMT", "RTX", "NOC", "BA"],
    "Healthcare": ["JNJ", "PFE", "MRNA", "UNH"],
    "Crypto": ["BTC", "ETH", "SOL"],
}

# News RSS feeds (financial focus) — all near real-time
RSS_FEEDS = [
    # Yahoo Finance
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^IXIC&region=US&lang=en-US",
    "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^DJI&region=US&lang=en-US",
    # Reuters
    "https://feeds.reuters.com/reuters/businessNews",
    "https://feeds.reuters.com/reuters/technologyNews",
    "https://feeds.reuters.com/reuters/topNews",
    # CNBC
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/10001147/device/rss/rss.html",
    "https://www.cnbc.com/id/15839069/device/rss/rss.html",  # Markets
    "https://www.cnbc.com/id/19854910/device/rss/rss.html",  # Finance
    # MarketWatch
    "https://www.marketwatch.com/rss/topstories",
    "https://feeds.marketwatch.com/marketwatch/marketpulse/",
    "https://www.marketwatch.com/rss/realtimeheadlines",
    # Investing.com
    "https://www.investing.com/rss/news.rss",
    "https://www.investing.com/rss/news_25.rss",  # US stocks
    "https://www.investing.com/rss/news_14.rss",  # Technology
    # BBC Business
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    # FT
    "https://www.ft.com/?format=rss",
    # Seeking Alpha
    "https://seekingalpha.com/market_currents.xml",
    # Bloomberg (public)
    "https://feeds.bloomberg.com/markets/news.rss",
    "https://feeds.bloomberg.com/technology/news.rss",
    # The Street
    "https://www.thestreet.com/rss/index.xml",
    # Barron's
    "https://www.barrons.com/xml/rss/3_7510.xml",
]

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

def load_state():
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        # Expirar cache de artículos vistos cada 90 minutos
        last_run = state.get("last_run")
        if last_run:
            try:
                last_dt = datetime.fromisoformat(last_run)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                age_minutes = (datetime.now(timezone.utc) - last_dt).total_seconds() / 60
                if age_minutes > 90:
                    state["seen_articles"] = []  # Reset cache
            except:
                pass
        return state
    return {"last_run": None, "seen_articles": []}

def save_state(state):
    state_copy = state.copy()
    # Keep only last 500 seen articles to avoid bloat
    state_copy["seen_articles"] = state_copy.get("seen_articles", [])[-500:]
    STATE_FILE.write_text(json.dumps(state_copy, indent=2))

def fetch_url(url, timeout=10):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MarketAnalyst/1.0)",
            "Accept": "application/rss+xml, application/xml, text/xml, */*"
        })
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return None

def parse_rss(xml_text):
    """Simple RSS parser without external deps."""
    items = []
    if not xml_text:
        return items
    
    # Extract items
    item_pattern = re.compile(r'<item>(.*?)</item>', re.DOTALL | re.IGNORECASE)
    title_pattern = re.compile(r'<title[^>]*><!\[CDATA\[(.*?)\]\]>|<title[^>]*>(.*?)</title>', re.DOTALL | re.IGNORECASE)
    desc_pattern = re.compile(r'<description[^>]*><!\[CDATA\[(.*?)\]\]>|<description[^>]*>(.*?)</description>', re.DOTALL | re.IGNORECASE)
    link_pattern = re.compile(r'<link[^>]*>(.*?)</link>|<link[^>]*/>', re.DOTALL | re.IGNORECASE)
    date_pattern = re.compile(r'<pubDate[^>]*>(.*?)</pubDate>', re.DOTALL | re.IGNORECASE)
    
    for item_match in item_pattern.finditer(xml_text):
        item_text = item_match.group(1)
        
        title_m = title_pattern.search(item_text)
        title = (title_m.group(1) or title_m.group(2) or "").strip() if title_m else ""
        title = re.sub(r'<[^>]+>', '', title).strip()
        
        desc_m = desc_pattern.search(item_text)
        desc = (desc_m.group(1) or desc_m.group(2) or "").strip() if desc_m else ""
        desc = re.sub(r'<[^>]+>', '', desc).strip()[:500]
        
        link_m = link_pattern.search(item_text)
        link = (link_m.group(1) or "").strip() if link_m else ""
        
        date_m = date_pattern.search(item_text)
        pub_date = (date_m.group(1) or "").strip() if date_m else ""
        
        if title:
            items.append({
                "title": title,
                "description": desc,
                "link": link,
                "pub_date": pub_date
            })
    
    return items[:20]  # Max 20 per feed

def fetch_newsapi(api_key, query, from_hours=2):
    """Fetch from NewsAPI."""
    from_time = (datetime.now(timezone.utc) - timedelta(hours=from_hours)).strftime("%Y-%m-%dT%H:%M:%S")
    params = urllib.parse.urlencode({
        "q": query,
        "from": from_time,
        "sortBy": "publishedAt",
        "language": "en",
        "apiKey": api_key,
        "pageSize": 20
    })
    url = f"https://newsapi.org/v2/everything?{params}"
    data = fetch_url(url)
    if not data:
        return []
    try:
        result = json.loads(data)
        articles = result.get("articles", [])
        return [{
            "title": a.get("title", ""),
            "description": a.get("description", "") or "",
            "link": a.get("url", ""),
            "pub_date": a.get("publishedAt", ""),
            "source": a.get("source", {}).get("name", "NewsAPI")
        } for a in articles if a.get("title")]
    except:
        return []

def fetch_brave_search(api_key, query):
    """Fetch from Brave Search API."""
    params = urllib.parse.urlencode({"q": query, "count": 10, "freshness": "ph"})
    url = f"https://api.search.brave.com/res/v1/news/search?{params}"
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
            "X-Subscription-Token": api_key
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("results", [])
        return [{
            "title": r.get("title", ""),
            "description": r.get("description", "") or "",
            "link": r.get("url", ""),
            "pub_date": r.get("age", ""),
            "source": r.get("source", "Brave")
        } for r in results if r.get("title")]
    except Exception as e:
        return []

def collect_news(config, state):
    """Collect news from all sources."""
    all_articles = []
    seen = set(state.get("seen_articles", []))
    newsapi_key = config.get("newsapi_key", "")
    brave_key = config.get("brave_key", "")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching RSS feeds...", file=sys.stderr)
    
    # RSS feeds
    for feed_url in RSS_FEEDS:
        xml = fetch_url(feed_url)
        items = parse_rss(xml)
        for item in items:
            uid = item["title"][:80]
            if uid not in seen:
                item["source"] = feed_url.split("/")[2]
                all_articles.append(item)
    
    # NewsAPI — plan gratuito tiene delay 24h, usamos ventana amplia
    if newsapi_key and newsapi_key != "PENDING":
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching NewsAPI...", file=sys.stderr)
        queries = [
            "stock market earnings Fed interest rates",
            "NVIDIA Tesla Apple Google Microsoft",
            "Iberdrola Spain economy European stocks",
            "geopolitics trade war tariffs oil OPEC",
            "crypto bitcoin ethereum",
        ]
        for q in queries:
            articles = fetch_newsapi(newsapi_key, q, from_hours=24)
            for a in articles:
                uid = a["title"][:80]
                if uid not in seen:
                    all_articles.append(a)

    # Brave Search
    if brave_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Brave Search...", file=sys.stderr)
        brave_queries = [
            "stock market news today",
            "NVIDIA Netflix Google Iberdrola stock news",
            "global market movers today",
        ]
        for q in brave_queries:
            articles = fetch_brave_search(brave_key, q)
            for a in articles:
                uid = a["title"][:80]
                if uid not in seen:
                    all_articles.append(a)

    # Deduplicate by title
    seen_titles = set()
    unique = []
    for a in all_articles:
        key = a["title"][:80]
        if key not in seen_titles:
            seen_titles.add(key)
            unique.append(a)

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Collected {len(unique)} new articles.", file=sys.stderr)
    return unique

def format_articles_for_analysis(articles):
    """Format articles into a compact text for LLM analysis."""
    lines = []
    for i, a in enumerate(articles[:80], 1):  # Max 80 articles to avoid token bloat
        title = a.get("title", "")
        desc = a.get("description", "")[:200]
        source = a.get("source", "")
        pub = a.get("pub_date", "")[:16]
        lines.append(f"{i}. [{source}] {title}")
        if desc:
            lines.append(f"   {desc}")
    return "\n".join(lines)

def analyze_with_claude(articles_text, portfolio):
    """Use Claude via OpenClaw to analyze articles. Output JSON."""
    prompt = f"""Eres un analista financiero experto. Analiza estas noticias recientes de los últimos 60-90 minutos y genera recomendaciones de inversión accionables.

PORTFOLIO ACTUAL del usuario: {', '.join(portfolio)}

NOTICIAS RECIENTES:
{articles_text}

Genera un análisis JSON con esta estructura exacta:
{{
  "market_summary": "Resumen ejecutivo del estado de mercado en 2-3 frases",
  "sentiment": "bullish|bearish|neutral",
  "key_themes": ["tema1", "tema2", "tema3"],
  "recommendations": [
    {{
      "action": "BUY|SELL|HOLD|WATCH",
      "ticker": "SYMBOL",
      "company": "Nombre",
      "sector": "Sector",
      "price_target": "corto plazo",
      "confidence": "HIGH|MEDIUM|LOW",
      "reasoning": "Explicación concisa basada en noticias específicas",
      "risk": "Principal riesgo",
      "news_drivers": ["noticia1", "noticia2"],
      "in_portfolio": true/false
    }}
  ],
  "macro_alerts": ["alerta macro importante 1", "alerta macro 2"],
  "sectors_to_watch": {{
    "positive": ["sector1", "sector2"],
    "negative": ["sector1"]
  }}
}}

Reglas:
- Máximo 8 recomendaciones, prioriza las de HIGH confidence y las del portfolio
- Solo incluye recomendaciones con fundamento real en las noticias
- Si no hay noticias suficientes para recomendar algo, no lo incluyas
- BUY = noticia claramente positiva para la acción
- SELL = noticia claramente negativa, riesgo elevado
- WATCH = situación a monitorear, potencial entrada/salida próxima
- Responde SOLO con el JSON, sin markdown ni texto adicional"""

    # Write to temp file and call claude via API
    import subprocess
    import tempfile
    
    # Use the OpenClaw claude API endpoint if available, otherwise return raw articles
    try:
        # Try using the openclaw CLI
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(prompt)
            tmp_path = f.name
        
        # Use curl to call the API directly — OpenClaw exposes a local API
        result = subprocess.run(
            ["node", "-e", f"""
const fs = require('fs');
const https = require('https');
// Fallback: just output that we need external analysis
console.log(JSON.stringify({{
  market_summary: "Análisis pendiente - {len(articles_text.split(chr(10)))} noticias recopiladas",
  sentiment: "neutral",
  key_themes: [],
  recommendations: [],
  macro_alerts: [],
  sectors_to_watch: {{positive: [], negative: []}}
}}));
"""],
            capture_output=True, text=True, timeout=10
        )
        return json.loads(result.stdout)
    except:
        return None

def format_telegram_message(analysis, articles_count):
    """Format analysis for Telegram."""
    if not analysis:
        return None
    
    sentiment_emoji = {"bullish": "🟢", "bearish": "🔴", "neutral": "🟡"}.get(analysis.get("sentiment", "neutral"), "🟡")
    
    lines = [
        f"📊 *MARKET PULSE* — {datetime.now().strftime('%H:%M')} CET",
        f"{sentiment_emoji} Sentimiento: *{analysis.get('sentiment', 'neutral').upper()}*",
        f"📰 {articles_count} noticias analizadas",
        "",
        f"*Resumen:* {analysis.get('market_summary', '')}",
    ]
    
    # Key themes
    themes = analysis.get("key_themes", [])
    if themes:
        lines.append(f"\n🔑 *Temas clave:* {' · '.join(themes[:3])}")
    
    # Macro alerts
    macro = analysis.get("macro_alerts", [])
    if macro:
        lines.append("\n⚠️ *Alertas macro:*")
        for alert in macro[:3]:
            lines.append(f"  • {alert}")
    
    # Recommendations
    recs = analysis.get("recommendations", [])
    if recs:
        lines.append("\n💡 *Recomendaciones:*")
        for r in recs[:6]:
            action = r.get("action", "")
            action_emoji = {"BUY": "🟢 COMPRAR", "SELL": "🔴 VENDER", "HOLD": "⏸ MANTENER", "WATCH": "👁 VIGILAR"}.get(action, action)
            conf = r.get("confidence", "")
            conf_emoji = {"HIGH": "🔥", "MEDIUM": "📍", "LOW": "💭"}.get(conf, "")
            portfolio_mark = " ★" if r.get("in_portfolio") else ""
            
            lines.append(f"\n*{action_emoji}* — {r.get('company', '')} `{r.get('ticker', '')}`{portfolio_mark} {conf_emoji}")
            lines.append(f"  _{r.get('reasoning', '')}_")
            lines.append(f"  ⚡ Riesgo: {r.get('risk', 'N/A')}")
    
    # Sectors
    sectors = analysis.get("sectors_to_watch", {})
    pos = sectors.get("positive", [])
    neg = sectors.get("negative", [])
    if pos or neg:
        lines.append("\n📈 *Sectores:*")
        if pos:
            lines.append(f"  Positivo: {', '.join(pos)}")
        if neg:
            lines.append(f"  Negativo: {', '.join(neg)}")
    
    lines.append(f"\n_★ = en tu portfolio_")
    
    return "\n".join(lines)

def main():
    config = load_config()
    state = load_state()
    
    # Collect news
    articles = collect_news(config, state)
    
    if not articles:
        print(json.dumps({"status": "no_new_articles", "message": "No hay noticias nuevas"}))
        return
    
    # Format for analysis
    articles_text = format_articles_for_analysis(articles)
    
    # Update seen articles
    state["seen_articles"] = state.get("seen_articles", []) + [a["title"][:80] for a in articles]
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    
    # Output articles for external analysis (OpenClaw cron will handle LLM)
    output = {
        "status": "ok",
        "articles_count": len(articles),
        "articles_text": articles_text,
        "portfolio": PORTFOLIO,
        "timestamp": datetime.now().isoformat()
    }
    
    print(json.dumps(output))

if __name__ == "__main__":
    main()
