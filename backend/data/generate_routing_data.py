"""
Generates a synthetic hour-by-hour success-rate time series for a single
day, simulating a realistic "peak hours bank server degradation" pattern:
normal ~85-92% success rate most of the day, dropping sharply during a
peak-traffic window (e.g. lunch/evening) when the primary bank rail is
overloaded.
"""

import csv
import random

random.seed(11)


def generate(degraded_hours=(13, 14, 19, 20)):
    rows = []
    for hour in range(24):
        attempted = random.randint(80, 260)

        if hour in degraded_hours:
            # Peak-hour degradation: success rate craters
            success_rate = random.uniform(0.35, 0.45)
        else:
            success_rate = random.uniform(0.82, 0.93)

        succeeded = int(attempted * success_rate)

        rows.append(
            {
                "hour": hour,
                "attempted": attempted,
                "succeeded": succeeded,
                "success_rate": round(succeeded / attempted, 3),
                "primary_rail": "bank_rail_A",
            }
        )
    return rows


def main():
    rows = generate()
    out_path = __file__.replace(
        "generate_routing_data.py", "hourly_success_rate.csv"
    )
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} hourly success-rate rows to {out_path}")


if __name__ == "__main__":
    main()
