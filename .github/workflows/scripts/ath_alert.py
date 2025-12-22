import os
import yfinance as yf
import smtplib
from email.mime.text import MIMEText

stocks = os.getenv("STOCKS").split(",")

rows = []

for stock in stocks:
    ticker = yf.Ticker(stock.strip())
    hist = ticker.history(period="max")

    if hist.empty:
        continue

    ath = hist["Close"].max()
    current = hist["Close"].iloc[-1]

    decline_pct = ((ath - current) / ath) * 100

    for level in [5, 10, 15]:
        if decline_pct >= level:
            rows.append({
                "stock": stock.strip(),
                "ath": ath,
                "current": current,
                "decline": decline_pct
            })
            break

if not rows:
    print("No alerts triggered.")
    exit(0)

# 🔽 Sort by highest decline
rows.sort(key=lambda x: x["decline"], reverse=True)

# ---------- HTML EMAIL ----------
html_body = """
<html>
<body>
  <h3>📉 Stocks Down From All-Time High</h3>
  <table border="1" cellpadding="8" cellspacing="0"
         style="border-collapse:collapse; font-family:Arial;">
    <tr style="background-color:#eaeaea;">
      <th>Stock Name</th>
      <th>ATH Price (₹)</th>
      <th>Current Price (₹)</th>
      <th>Declined (%)</th>
    </tr>
"""

for r in rows:
    row_color = "#ffcccc" if r["decline"] > 10 else "#ffffff"

    html_body += f"""
    <tr style="background-color:{row_color};">
      <td>{r['stock']}</td>
      <td>₹{r['ath']:.2f}</td>
      <td>₹{r['current']:.2f}</td>
      <td>{r['decline']:.2f}%</td>
    </tr>
    """

html_body += """
  </table>
  <p style="font-size:12px;color:#666;">
    🔴 Rows highlighted in red indicate a decline greater than 10% from ATH.
  </p>
</body>
</html>
"""

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

print("Alert email sent.")
