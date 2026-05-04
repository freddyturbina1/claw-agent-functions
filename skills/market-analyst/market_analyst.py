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

def parse_pub_date(date_str):
    """Parse pubDate string to UTC datetime. Returns None if unparseable."""
    if not date_str:
        return None
    # Common RSS date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",   # RFC 822: Mon, 04 May 2026 10:30:00 +0000
        "%a, %d %b %Y %H:%M:%S GMT",   # Mon, 04 May 2026 10:30:00 GMT
        "%Y-%m-%dT%H:%M:%S%z",         # ISO 8601: 2026-05-04T10:30:00+00:00
        "%Y-%m-%dT%H:%M:%SZ",          # ISO 8601 UTC: 2026-05-04T10:30:00Z
        "%Y-%m-%d %H:%M:%S",           # Simple: 2026-05-04 10:30:00
    ]
    date_str = date_str.strip()
    # Normalize "GMT" to "+0000"
    date_str_norm = date_str.replace("GMT", "+0000").replace("UTC", "+0000")
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str_norm, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except:
            continue
    return None

def is_recent(pub_date_str, max_minutes=90):
    """Returns True if article is within max_minutes, or if date is unparseable (benefit of doubt)."""
    dt = parse_pub_date(pub_date_str)
    if dt is None:
        return True  # Can't parse → include (better false positive than miss)
    age_minutes = (datetime.now(timezone.utc) - dt).total_seconds() / 60
    return age_minutes <= max_minutes

def parse_rss(xml_text, max_age_minutes=90):
    """Simple RSS parser without external deps. Filters by pubDate age."""
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
        
        if title and is_recent(pub_date, max_age_minutes):
            items.append({
                "title": title,
                "description": desc,
                "link": link,
                "pub_date": pub_date
            })
    
    return items[:20]  # Max 20 per feed

def fetch_alphavantage(api_key, max_age_minutes=90):
    """Fetch market news from Alpha Vantage (real-time, per ticker)."""
    tickers = "NVDA,NFLX,INTC,TSLA,MSFT,AAPL,GOOGL,AMZN,META,AMD,COIN,CVX,MRK"
    url = f"https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={tickers}&limit=50&apikey={api_key}"
    data = fetch_url(url)
    if not data:
        return []
    try:
        result = json.loads(data)
        articles = result.get("feed", [])
        items = []
        for a in articles:
            pub_date = a.get("time_published", "")  # Format: 20260504T103000
            # Convert to parseable format
            if len(pub_date) == 15:
                pub_date = f"{pub_date[:4]}-{pub_date[4:6]}-{pub_date[6:8]}T{pub_date[9:11]}:{pub_date[11:13]}:{pub_date[13:15]}Z"
            if not is_recent(pub_date, max_age_minutes):
                continue
            items.append({
                "title": a.get("title", ""),
                "description": a.get("summary", "")[:300],
                "link": a.get("url", ""),
                "pub_date": pub_date,
                "source": a.get("source", "AlphaVantage")
            })
        return items
    except:
        return []

def fetch_finnhub(api_key, max_age_minutes=90):
    """Fetch market news from Finnhub (real-time general market news)."""
    url = f"https://finnhub.io/api/v1/news?category=general&token={api_key}"
    data = fetch_url(url)
    if not data:
        return []
    try:
        articles = json.loads(data)
        items = []
        for a in articles:
            # Finnhub uses Unix timestamp
            ts = a.get("datetime", 0)
            if ts:
                dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                age_minutes = (datetime.now(timezone.utc) - dt).total_seconds() / 60
                if age_minutes > max_age_minutes:
                    continue
                pub_date = dt.isoformat()
            else:
                pub_date = ""
            title = a.get("headline", "")
            if title:
                items.append({
                    "title": title,
                    "description": a.get("summary", "")[:300],
                    "link": a.get("url", ""),
                    "pub_date": pub_date,
                    "source": a.get("source", "Finnhub")
                })
        return items
    except:
        return []

def fetch_polygon(api_key, max_age_minutes=90):
    """Fetch market news from Polygon.io."""
    from_time = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    tickers = "NVDA,NFLX,INTC,TSLA,AAPL,MSFT,GOOGL,META,AMZN,AMD,CVX,MRK,COIN"
    params = urllib.parse.urlencode({
        "ticker.any_of": tickers,
        "published_utc.gte": from_time,
        "order": "desc",
        "limit": 50,
        "apiKey": api_key
    })
    url = f"https://api.polygon.io/v2/reference/news?{params}"
    data = fetch_url(url)
    if not data:
        return []
    try:
        result = json.loads(data)
        articles = result.get("results", [])
        items = []
        for a in articles:
            title = a.get("title", "")
            if title:
                items.append({
                    "title": title,
                    "description": a.get("description", "")[:300],
                    "link": a.get("article_url", ""),
                    "pub_date": a.get("published_utc", ""),
                    "source": a.get("publisher", {}).get("name", "Polygon")
                })
        return items
    except:
        return []

def fetch_thenewsapi(api_key, max_age_minutes=90):
    """Fetch financial news from TheNewsAPI."""
    from_time = (datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)).strftime("%Y-%m-%dT%H:%M:%S")
    params = urllib.parse.urlencode({
        "api_token": api_key,
        "categories": "business,tech",
        "language": "en",
        "published_after": from_time,
        "sort": "published_at",
        "limit": 50
    })
    url = f"https://api.thenewsapi.com/v1/news/all?{params}"
    data = fetch_url(url)
    if not data:
        return []
    try:
        result = json.loads(data)
        articles = result.get("data", [])
        items = []
        for a in articles:
            title = a.get("title", "")
            if title:
                items.append({
                    "title": title,
                    "description": a.get("description", "")[:300],
                    "link": a.get("url", ""),
                    "pub_date": a.get("published_at", ""),
                    "source": a.get("source", "TheNewsAPI")
                })
        return items
    except:
        return []

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

def collect_news(config, state, max_age_minutes=90):
    """Collect news from all sources."""
    all_articles = []
    seen = set(state.get("seen_articles", []))
    newsapi_key = config.get("newsapi_key", "")
    brave_key = config.get("brave_key", "")

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching RSS feeds (max_age={max_age_minutes}min)...", file=sys.stderr)
    
    # RSS feeds
    for feed_url in RSS_FEEDS:
        xml = fetch_url(feed_url)
        items = parse_rss(xml, max_age_minutes=max_age_minutes)
        for item in items:
            uid = item["title"][:80]
            if uid not in seen:
                item["source"] = feed_url.split("/")[2]
                all_articles.append(item)
    
    # Alpha Vantage — noticias por ticker con sentimiento, tiempo real
    alphavantage_key = config.get("alphavantage_key", "")
    if alphavantage_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Alpha Vantage...", file=sys.stderr)
        for a in fetch_alphavantage(alphavantage_key, max_age_minutes):
            uid = a["title"][:80]
            if uid not in seen:
                all_articles.append(a)

    # Finnhub — noticias generales de mercado, tiempo real
    finnhub_key = config.get("finnhub_key", "")
    if finnhub_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Finnhub...", file=sys.stderr)
        for a in fetch_finnhub(finnhub_key, max_age_minutes):
            uid = a["title"][:80]
            if uid not in seen:
                all_articles.append(a)

    # Polygon.io — noticias por ticker
    polygon_key = config.get("polygon_key", "")
    if polygon_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching Polygon...", file=sys.stderr)
        for a in fetch_polygon(polygon_key, max_age_minutes):
            uid = a["title"][:80]
            if uid not in seen:
                all_articles.append(a)

    # TheNewsAPI — business + tech news
    thenewsapi_key = config.get("thenewsapi_key", "")
    if thenewsapi_key:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Fetching TheNewsAPI...", file=sys.stderr)
        for a in fetch_thenewsapi(thenewsapi_key, max_age_minutes):
            uid = a["title"][:80]
            if uid not in seen:
                all_articles.append(a)

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

    # Mode: "event" = 25 min window (evento-driven), default = 90 min (programados)
    mode = os.environ.get("ANALYST_MODE", "scheduled")
    max_age = 25 if mode == "event" else 90
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Mode: {mode} | max_age: {max_age} min", file=sys.stderr)

    # Collect news
    articles = collect_news(config, state, max_age_minutes=max_age)
    
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
