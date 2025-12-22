import os
import yfinance as yf
import smtplib
from email.mime.text import MIMEText

# ---------- CONFIG ----------
DECLINE_LEVELS = [5, 10, 15]

# ---------- READ STOCKS ----------
stocks_env = os.getenv("STOCKS", "")
if not stocks_env:
    print("No STOCKS provided.")
    exit(0)

stocks = [s.strip() for s in stocks_env.split(",") if s.strip()]

rows = []

# ---------- FETCH DATA ----------
for stock in stocks:
    try:
        ticker = yf.Ticker(stock)
        hist = ticker.history(period="max")

        if hist.empty or "Close" not in hist:
            continue

        ath = hist["Close"].max()
        current = hist["Close"].iloc[-1]

        if ath <= 0:
            continue

        decline_pct = ((ath - current) / ath) * 100

        for level in DECLINE_LEVELS:
            if decline_pct >= level:
                rows.append({
                    "stock": stock,
                    "ath": ath,
                    "current": current,
                    "decline": decline_pct
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
      <th>Current Price (₹)</th>
      <th>Declined (%)</th>
    </tr>
"""

for r in rows:
    if r["decline"] >= 15:
        row_color = "#ff4d4d"   # dark red
    elif r["decline"] >= 10:
        row_color = "#ff9999"   # medium red
    elif r["decline"] >= 5:
        row_color = "#ffd6d6"   # light red
    else:
        row_color = "#ffffff"

    html_body += f"""
    <tr style="background-color:{row_color};">
      <td>{r['stock']}</td>
      <td>₹{r['ath']:.2f}</td>
      <td>₹{r['current']:.2f}</td>
      <td><b>{r['decline']:.2f}%</b></td>
    </tr>
    """

html_body += """
  </table>

  <br>
  <b>Legend:</b>
  <ul style="font-size:12px;">
    <li style="color:#ff4d4d;">■ ≥ 15% decline (Strong correction)</li>
    <li style="color:#ff9999;">■ 10–15% decline</li>
    <li style="color:#ffd6d6;">■ 5–10% decline</li>
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
