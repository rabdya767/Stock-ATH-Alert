import requests
import pandas as pd
import smtplib
import os
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ------------------ CONFIG ------------------
STATE_FILE = "state.json"
THRESHOLDS = [2, 5, 10, 20]

EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO   = os.getenv("EMAIL_TO")
INPUT_SCHEMES = os.getenv("INPUT_SCHEMES", "").strip()

# ------------------ DEFAULT JIO FUNDS ------------------
JIOBLACKROCK_FUNDS = {
    "JioBlackRock Nifty 50 Index Fund - Direct Growth": "INF22M001044",
    "JioBlackRock Nifty Next 50 Index Fund - Direct Growth": "INF22M001085",
    "JioBlackRock Nifty Midcap 150 Index Fund - Direct Growth": "INF22M001077",
    "JioBlackRock Nifty Smallcap 250 Index Fund - Direct Growth": "INF22M001051",
    "JioBlackRock Nifty 8-13 yr G-Sec Index Fund - Direct Growth": "INF22M001069",
    "JioBlackRock Flexi Cap Fund - Direct Growth": "INF22M001093",
    "JioBlackRock Money Market Fund - Direct Growth": "INF22M001028",
}

# ------------------ ADDITIONAL FUNDS ------------------
ADDITIONAL_FUNDS = {
    "Helios Small Cap Fund - Direct Growth": "INF0R8701384"
}

# ------------------ COMBINE SCHEMES ------------------
SCHEMES_TO_USE = JIOBLACKROCK_FUNDS.copy()
if INPUT_SCHEMES:
    user_selected = [name.strip() for name in INPUT_SCHEMES.split(",")]
    for name in user_selected:
        if name in ADDITIONAL_FUNDS:
            SCHEMES_TO_USE[name] = ADDITIONAL_FUNDS[name]

# ------------------ STATE FUNCTIONS ------------------
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, default=str)

# ------------------ NAV FETCH ------------------
def fetch_nav_history(code):
    url = f"https://api.mfapi.in/mf/{code}"
    data = requests.get(url).json()
    df = pd.DataFrame(data["data"])
    df["nav"] = df["nav"].astype(float)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    return df.sort_values("date")

# ------------------ ANALYSIS ------------------
def analyze_fund(name, code, state):
    df = fetch_nav_history(code)

    ath_row = df.loc[df["nav"].idxmax()]
    latest_row = df.iloc[-1]

    ath_nav = ath_row.nav
    ath_date = ath_row.date.date()
    current_nav = latest_row.nav
    current_date = latest_row.date.date()

    decline = ((ath_nav - current_nav) / ath_nav) * 100

    fund_state = state.get(name, {
        "ath_nav": ath_nav,
        "ath_date": str(ath_date),
        "last_alert": 0
    })

    # Reset alerts if new ATH
    if ath_nav > fund_state["ath_nav"]:
        fund_state["ath_nav"] = ath_nav
        fund_state["ath_date"] = str(ath_date)
        fund_state["last_alert"] = 0

    triggered = [
        t for t in THRESHOLDS
        if decline >= t and t > fund_state["last_alert"]
    ]

    if triggered:
        fund_state["last_alert"] = max(triggered)

    state[name] = fund_state

    if triggered:
        return {
            "Fund": name,
            "ATH NAV": ath_nav,
            "ATH Date": ath_date,
            "Current NAV": current_nav,
            "NAV Date": current_date,
            "Decline %": round(decline, 2),
            "Triggered Level": f"{max(triggered)}%"
        }

    return None

# ------------------ EMAIL ------------------
def send_email(df):
    # Start HTML table
    html = """
    <html>
      <body>
        <p>The following mutual funds have declined from their ATH:</p>
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
          <tr>
            <th>Fund</th>
            <th>ATH NAV</th>
            <th>ATH Date</th>
            <th>Current NAV</th>
            <th>NAV Date</th>
            <th>Decline %</th>
            <th>Triggered Level</th>
          </tr>
    """

    for _, row in df.iterrows():
        decline = row['Decline %']
        if decline > 10:
            bgcolor = '#8B0000'  # Deep red
            font_color = 'white'
        elif decline >= 5:
            bgcolor = '#FF0000'  # Red
            font_color = 'white'
        elif decline >= 3:
            bgcolor = '#FF7F7F'  # Light red
            font_color = 'black'
        else:
            bgcolor = 'white'
            font_color = 'black'

        html += f"""
        <tr style="background-color:{bgcolor}; color:{font_color}; font-weight:bold;">
            <td>{row['Fund']}</td>
            <td>{row['ATH NAV']}</td>
            <td>{row['ATH Date']}</td>
            <td>{row['Current NAV']}</td>
            <td>{row['NAV Date']}</td>
            <td>{row['Decline %']}</td>
            <td>{row['Triggered Level']}</td>
        </tr>
        """

    html += """
        </table>
      </body>
    </html>
    """

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_TO
    msg["Subject"] = "📉 Mutual Fund Drawdown Alert"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

# ------------------ MAIN ------------------
state = load_state()
alerts = []

for name, code in SCHEMES_TO_USE.items():
    result = analyze_fund(name, code, state)
    if result:
        alerts.append(result)

if alerts:
    df_alerts = pd.DataFrame(alerts)
    send_email(df_alerts)

save_state(state)
