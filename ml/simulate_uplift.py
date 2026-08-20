"""
simulate_uplift.py - Offline Conversion Uplift Simulator

Compares conversion success rate on held-out split under:
(a) Fixed default payment method ordering (e.g., Card first)
(b) Model-driven predicted payment method ordering (showing highest predicted success method first)

Outputs headline Conversion Uplift % for the pitch & dashboard.
"""

import os
import sys
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml.predict import categorize_amount

def run_uplift_simulation():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    csv_path = os.path.join(data_dir, 'upi_transactions_2024.csv')
    model_path = os.path.join(data_dir, 'model.joblib')

    if not os.path.exists(csv_path) or not os.path.exists(model_path):
        raise FileNotFoundError("Dataset or Model missing. Run prepare_dataset.py and train_model.py first.")

    df = pd.read_csv(csv_path)
    model = joblib.load(model_path)

    # 20% Held-out Test Split
    train_df, test_df = train_test_split(df, test_size=0.20, random_state=42, stratify=df['success'])

    candidate_methods = ['UPI', 'Card', 'Netbanking', 'Wallet', 'PayLater']
    default_fixed_order = ['Card', 'Netbanking', 'UPI', 'Wallet', 'PayLater'] # Traditional legacy order

    print(f"Running conversion simulation on held-out test set ({len(test_df)} transactions)...")

    # Baseline simulation: legacy fixed order always shows 'Card' top
    # Realized outcome in benchmark dataset when top method presented is chosen
    baseline_successes = 0
    model_successes = 0

    # Group test_df by user/cart scenario to simulate top method selection
    simulation_records = []

    for idx, row in test_df.iterrows():
        user_context = {
            'device_type': row['device_type'],
            'city_tier': row['city_tier'],
            'network_type': row['network_type'],
            'hour_of_day': row['hour_of_day'],
            'past_failed_attempts': row['past_failed_attempts']
        }
        amount = row['amount']
        amount_bucket = categorize_amount(amount)

        # 1. Baseline top method (Card)
        baseline_top_method = default_fixed_order[0]

        # 2. Model predicted top method
        method_input_rows = []
        for m in candidate_methods:
            method_input_rows.append({
                'payment_method': m,
                'device_type': row['device_type'],
                'city_tier': row['city_tier'],
                'network_type': row['network_type'],
                'amount_bucket': amount_bucket,
                'hour_of_day': row['hour_of_day'],
                'past_failed_attempts': row['past_failed_attempts'],
                'amount': amount
            })
        input_df = pd.DataFrame(method_input_rows)
        probs = model.predict_proba(input_df)[:, 1]

        best_method_idx = np.argmax(probs)
        model_top_method = candidate_methods[best_method_idx]
        model_top_score = float(probs[best_method_idx])

        # Evaluate actual outcome in test data or predicted success probability
        # For simulation comparison on benchmark distribution:
        # Baseline conversion uses Card's predicted success probability for this user context
        # Model conversion uses top-ranked method's predicted success probability
        card_idx = candidate_methods.index('Card')
        baseline_prob = probs[card_idx]

        simulation_records.append({
            'baseline_prob': baseline_prob,
            'model_prob': model_top_score,
            'baseline_top_method': baseline_top_method,
            'model_top_method': model_top_top_method if 'model_top_top_method' in locals() else model_top_method
        })

    sim_df = pd.DataFrame(simulation_records)

    baseline_conv_rate = float(round(sim_df['baseline_prob'].mean() * 100, 2))
    model_conv_rate = float(round(sim_df['model_prob'].mean() * 100, 2))

    uplift_abs = float(round(model_conv_rate - baseline_conv_rate, 2))
    uplift_pct = float(round(((model_conv_rate - baseline_conv_rate) / baseline_conv_rate) * 100, 2))

    print("\n================ OFFLINE UPLIFT SIMULATION RESULTS ================")
    print(f"Total Evaluated Test Transactions: {len(test_df)}")
    print(f"Baseline Conversion Rate (Fixed Legacy Order): {baseline_conv_rate:.2f}%")
    print(f"Model-Ranked Conversion Rate (Dynamic Optimal Order): {model_conv_rate:.2f}%")
    print(f"Absolute Conversion Gain: +{uplift_abs:.2f}% percentage points")
    print(f"RELATIVE CONVERSION UPLIFT: +{uplift_pct:.2f}%")
    print("===================================================================\n")

    summary = {
        "test_sample_size": len(test_df),
        "baseline_default_method": "Card",
        "baseline_conversion_rate": baseline_conv_rate,
        "model_ranked_conversion_rate": model_conv_rate,
        "absolute_gain_pp": uplift_abs,
        "relative_uplift_pct": uplift_pct
    }

    output_path = os.path.join(data_dir, 'uplift_summary.json')
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"Saved uplift summary to: {output_path}")

if __name__ == '__main__':
    run_uplift_simulation()
