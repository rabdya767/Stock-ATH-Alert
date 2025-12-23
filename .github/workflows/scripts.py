import requests
import pandas as pd
import os
import json

# ------------------ CONFIG ------------------
STATE_FILE = "state.json"
THRESHOLDS = [2, 5, 10, 20]

INPUT_SCHEMES = os.getenv("INPUT_SCHEMES", "").strip()
HEADERS = {"User-Agent": "Mozilla/5.0 (GitHub Actions)"}

# ------------------ DEFAULT FUNDS ------------------
JIOBLACKROCK_FUNDS = {
    "JioBlackRock Nifty 50 Index Fund - Direct Growth": "153787",
    "JioBlackRock Nifty Next 50 Index Fund - Direct Growth": "153789",
    "JioBlackRock Nifty Midcap 150 Index Fund - Direct Growth": "153788",
    "JioBlackRock Nifty Smallcap 250 Index Fund - Direct Growth": "153790",
    "JioBlackRock Flexi Cap Fund - Direct Growth": "153859",
    "Helios Small Cap Fund - Direct Plan - Growth": "153912"
}

ADDITIONAL_FUNDS = {
    "Helios Small Cap Fund - Direct Growth": "INF0R8701384"
}

# ------------------ COMBINE SCHEMES ------------------
SCHEMES_TO_USE = JIOBLACKROCK_FUNDS.copy()
if INPUT_SCHEMES:
    for name in [x.strip() for x in INPUT_SCHEMES.split(",")]:
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
    resp = requests.get(url, headers=HEADERS, timeout=10)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}")
    if not resp.text.strip():
        raise RuntimeError("Empty response")
    data = resp.json()
    if "data" not in data or not data["data"]:
        raise RuntimeError("No NAV data")
    df = pd.DataFrame(data["data"])
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna()
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

    fund_state = state.get(name, {"ath_nav": ath_nav, "ath_date": str(ath_date), "last_alert": 0})

    if ath_nav > fund_state["ath_nav"]:
        fund_state["ath_nav"] = ath_nav
        fund_state["ath_date"] = str(ath_date)
        fund_state["last_alert"] = 0

    triggered = [t for t in THRESHOLDS if decline >= t and t > fund_state["last_alert"]]

    if triggered:
        fund_state["last_alert"] = max(triggered)

    state[name] = fund_state

    return {
        "Fund": name,
        "ATH NAV": round(ath_nav, 2),
        "ATH Date": ath_date,
        "Current NAV": round(current_nav, 2),
        "NAV Date": current_date,
        "Decline %": round(decline, 2),
        "Triggered Level": f"{max(triggered)}%" if triggered else "-"
    }

# ------------------ MAIN ------------------
state = load_state()
alerts = []

for name, code in SCHEMES_TO_USE.items():
    try:
        print(f"Fetching {name} ({code})")
        result = analyze_fund(name, code, state)
        alerts.append(result)
    except Exception as e:
        print(f"❌ Skipping {name}: {e}")

# Convert to DataFrame for pretty printing
df_alerts = pd.DataFrame(alerts)
print("\n📊 Mutual Fund ATH Alerts:\n")
print(df_alerts.to_string(index=False))

# Save state
save_state(state)
print("\n✅ Script completed successfully")
