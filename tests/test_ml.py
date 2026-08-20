"""
test_ml.py - Unit tests for Part B Conversion Intelligence Model & Predictor
"""

import os
import sys
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ml.predict import predict_best_method, categorize_amount

def test_categorize_amount():
    assert categorize_amount(250) == 'low'
    assert categorize_amount(1500) == 'med'
    assert categorize_amount(5000) == 'high'
    assert categorize_amount(25000) == 'ultra_high'

def test_predict_best_method_structure():
    cart = {"amount": 1299.00}
    user_context = {
        "device_type": "Android",
        "city_tier": "Tier 2",
        "network_type": "4G",
        "hour_of_day": 16,
        "past_failed_attempts": 0
    }

    rankings = predict_best_method(cart, user_context)

    assert isinstance(rankings, list)
    assert len(rankings) == 5

    methods_returned = set()
    for item in rankings:
        assert 'method' in item
        assert 'predicted_success_prob' in item
        assert 'rank' in item
        assert 0.0 <= item['predicted_success_prob'] <= 1.0
        methods_returned.add(item['method'])

    assert methods_returned == {'UPI', 'Card', 'Netbanking', 'Wallet', 'PayLater'}
    # Ensure rankings are sorted descending
    probs = [item['predicted_success_prob'] for item in rankings]
    assert probs == sorted(probs, reverse=True)
