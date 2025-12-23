import os
import yfinance as yf
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

# ---------- CONFIG ----------
DECLINE_LEVELS = [2, 5, 7, 10, 15]
OLD_ATH_DAYS = 365

# ---------- READ STOCKS ----------
stocks_env = os.getenv("STOCKS", "")
if not stocks_env:
    print("No STOCKS provided.")
    exit(0)

stocks = [s.strip() for s in stocks_env.split(",") if s.strip()]
rows = []
today = datetime.now(timezone.utc).date()

# ---------- FETCH DATA ----------
for stock in stocks:
    try:
        ticker = yf.Ticker(stock)
        hist = ticker.history(period="max")

        if hist.empty or "Close" not in hist:
            continue

        close = hist["Close"]
        ath = close.max()
        ath_date = close.idxmax().date()
        current = close.iloc[-1]

        if ath <= 0:
            continue

        # Days since ATH
        days_since_ath = (today - ath_date).days

        # Decline from ATH
        decline_pct = ((ath - current) / ath) * 100

        # 52-week high
        hist_1y = ticker.history(period="1y")
        high_52w = hist_1y["High"].max() if not hist_1y.empty else None
        vs_52w = (
            ((high_52w - current) / high_52w) * 100
            if high_52w and high_52w > 0
            else None
        )

        for level in DECLINE_LEVELS:
            if decline_pct >= level:
                rows.append({
                    "stock": stock,
                    "ath": ath,
                    "ath_date": ath_date,
                    "days_since_ath": days_since_ath,
                    "current": current,
                    "decline": decline_pct,
                    "high_52w": high_52w,
                    "vs_52w": vs_52w
                })
                break

    except Exception as e:
        print(f"Error processing {stock}: {e}")

if not rows:
    print("No alerts triggered.")
    exit(0)

# ---------- SORT ----------
rows.sort(key=lambda x: x["decline"], reverse=True)

# ---------- HTML EMAIL ----------
html_body = """
<html>
<body style="font-family:Arial;">
  <h3>📉 Stocks Down From All-Time High</h3>

  <table border="1" cellpadding="8" cellspacing="0"
         style="border-collapse:collapse; width:100%;">
    <tr style="background-color:#eaeaea; font-weight:bold;">
      <th>Stock</th>
      <th>ATH Price (₹)</th>
      <th>ATH Date</th>
      <th>Current Price (₹)</th>
      <th>Declined from ATH (%)</th>
      <th>52W High vs Current (%)</th>
    </tr>
"""

for r in rows:
    # Decline-based coloring
    if r["decline"] >= 15:
        row_color = "#ff4d4d"
    elif r["decline"] >= 10:
        row_color = "#ff9999"
    elif r["decline"] >= 5:
        row_color = "#ffd6d6"
    else:
        row_color = "#ffffff"

    # Old ATH highlight (> 1 year)
    if r["days_since_ath"] > OLD_ATH_DAYS:
        row_color = "#fff3b0"  # yellow

    vs_52w_display = (
        f"{r['vs_52w']:.2f}%" if r["vs_52w"] is not None else "N/A"
    )

    html_body += f"""
    <tr style="background-color:{row_color};">
      <td>{r['stock']}</td>
      <td>₹{r['ath']:.2f}</td>
      <td>{r['ath_date']} ({r['days_since_ath']} days)</td>
      <td>₹{r['current']:.2f}</td>
      <td><b>{r['decline']:.2f}%</b></td>
      <td>{vs_52w_display}</td>
    </tr>
    """

html_body += """
  </table>

  <br>
  <b>Legend:</b>
  <ul style="font-size:12px;">
    <li style="color:#ff4d4d;">■ ≥ 15% decline from ATH</li>
    <li style="color:#ff9999;">■ 10–15% decline</li>
    <li style="color:#ffd6d6;">■ 5–10% decline</li>
    <li style="background-color:#fff3b0; display:inline-block; padding:2px 6px;">
        ATH older than 1 year
    </li>
  </ul>

  <p style="font-size:11px;color:#666;">
    Generated automatically by GitHub Actions
  </p>
</body>
</html>
"""

# ---------- SEND EMAIL ----------
msg = MIMEText(html_body, "html")
msg["Subject"] = "📉 Stock Alert: Down from ATH"
msg["From"] = os.getenv("EMAIL_FROM")
msg["To"] = os.getenv("EMAIL_TO")

with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
    server.starttls()
    server.login(
        os.getenv("SMTP_USERNAME"),
        os.getenv("SMTP_PASSWORD")
    )
    server.send_message(msg)

print("Alert email sent successfully.")
