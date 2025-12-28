# ---------- PRINT CONSOLE TABLE ----------
print("\n📉 Stocks Down From All-Time High\n")

header = (
    f"{'Stock':<12}"
    f"{'ATH':>10}"
    f"{'ATH Date':>14}"
    f"{'Current':>10}"
    f"{'Decline %':>12}"
    f"{'52W vs Cur %':>14}"
)
print(header)
print("-" * len(header))

for r in rows:
    vs_52w_display = (
        f"{r['vs_52w']:.2f}"
        if r["vs_52w"] is not None
        else "N/A"
    )

    print(
        f"{r['stock']:<12}"
        f"{r['ath']:>10.2f}"
        f"{str(r['ath_date']):>14}"
        f"{r['current']:>10.2f}"
        f"{r['decline']:>12.2f}"
        f"{vs_52w_display:>14}"
    )

print("\nTotal alerts:", len(rows))
