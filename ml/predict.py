"""
predict.py - Payment Method Ranking Prediction Engine

Provides model-driven payment-method ranking based on cart and user context.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from typing import Dict, List, Any

# Lazy-loaded model cache
_MODEL_CACHE = None

def get_model():
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        model_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'model.joblib')
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}. Train the model first via train_model.py.")
        _MODEL_CACHE = joblib.load(model_path)
    return _MODEL_CACHE

def categorize_amount(amount: float) -> str:
    if amount < 500:
        return 'low'
    elif amount <= 2000:
        return 'med'
    elif amount <= 10000:
        return 'high'
    else:
        return 'ultra_high'

def predict_best_method(cart: Dict[str, Any], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given a cart dictionary (with total amount) and user context, predicts success probability
    for each available payment method and returns methods ranked by predicted success probability.

    Parameters:
    - cart: {"amount": 1499.00, ...}
    - user_context: {
        "device_type": "Android" | "iOS" | "Desktop",
        "city_tier": "Tier 1" | "Tier 2" | "Tier 3",
        "network_type": "4G" | "5G" | "Wifi" | "3G",
        "hour_of_day": int (0-23),
        "past_failed_attempts": int (0+)
      }

    Returns:
    - List of dicts ordered by predicted_success_prob descending:
      [
        {"method": "UPI", "predicted_success_prob": 0.932, "rank": 1},
        {"method": "Wallet", "predicted_success_prob": 0.854, "rank": 2},
        ...
      ]
    """
    model = get_model()

    amount = float(cart.get('amount', 999.0))
    amount_bucket = categorize_amount(amount)

    device_type = user_context.get('device_type', 'Android')
    city_tier = user_context.get('city_tier', 'Tier 2')
    network_type = user_context.get('network_type', '4G')
    hour_of_day = int(user_context.get('hour_of_day', 14))
    past_failed_attempts = int(user_context.get('past_failed_attempts', 0))

    candidate_methods = ['UPI', 'Card', 'Netbanking', 'Wallet', 'PayLater']

    rows = []
    for method in candidate_methods:
        rows.append({
            'payment_method': method,
            'device_type': device_type,
            'city_tier': city_tier,
            'network_type': network_type,
            'amount_bucket': amount_bucket,
            'hour_of_day': hour_of_day,
            'past_failed_attempts': past_failed_attempts,
            'amount': amount
        })

    input_df = pd.DataFrame(rows)

    # Predict probabilities for class 1 (Success)
    probs = model.predict_proba(input_df)[:, 1]

    results = []
    for method, prob in zip(candidate_methods, probs):
        results.append({
            'method': method,
            'predicted_success_prob': float(round(prob, 4))
        })

    # Sort descending by predicted success probability
    results.sort(key=lambda x: x['predicted_success_prob'], reverse=True)

    # Assign rank
    for idx, item in enumerate(results, start=1):
        item['rank'] = idx

    return results

if __name__ == '__main__':
    sample_cart = {"amount": 850.0}
    sample_context = {
        "device_type": "Android",
        "city_tier": "Tier 2",
        "network_type": "4G",
        "hour_of_day": 19,
        "past_failed_attempts": 0
    }
    print("Testing predict_best_method with sample user context...")
    rankings = predict_best_method(sample_cart, sample_context)
    print(json.dumps(rankings, indent=2))
