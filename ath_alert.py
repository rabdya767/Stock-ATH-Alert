import os
import yfinance as yf
import smtplib
from email.mime.text import MIMEText

stocks = os.getenv("STOCKS").split(",")

alerts = []

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
            alerts.append(
                f"{stock}: Down {decline_pct:.2f}% from ATH\n"
                f"ATH: ₹{ath:.2f}, Current: ₹{current:.2f}"
            )
            break

if not alerts:
    print("No alerts triggered.")
    exit(0)

email_body = "\n\n".join(alerts)

msg = MIMEText(email_body)
print(email_body)
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
