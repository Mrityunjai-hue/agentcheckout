"""
train_model.py - Conversion Intelligence Model Training Pipeline

Trains a Gradient Boosting Classifier to predict payment success probability based on context.
Handles class imbalance explicitly (imbalanced-learn SMOTE / class weighting).
Evaluates ROC-AUC, Precision, Recall, and F1 score on a held-out test split.
Saves model pipeline to data/model.joblib.
"""

import os
import json
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import roc_auc_score, classification_report, confusion_matrix, precision_recall_fscore_support
from imblearn.over_sampling import SMOTE
from imblearn.pipeline import Pipeline as ImbPipeline

def train_conversion_model():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    csv_path = os.path.join(data_dir, 'upi_transactions_2024.csv')

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Dataset not found at {csv_path}. Run prepare_dataset.py first.")

    df = pd.read_csv(csv_path)

    # Define Feature Sets
    categorical_features = ['payment_method', 'device_type', 'city_tier', 'network_type', 'amount_bucket']
    numeric_features = ['hour_of_day', 'past_failed_attempts', 'amount']
    target_col = 'success'

    X = df[categorical_features + numeric_features]
    y = df[target_col]

    # Stratified Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Column Preprocessor
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(drop='first', handle_unknown='ignore', sparse_output=False), categorical_features),
            ('num', StandardScaler(), numeric_features)
        ]
    )

    # Model Pipeline with SMOTE for handling class imbalance
    pipeline = ImbPipeline(steps=[
        ('preprocessor', preprocessor),
        ('smote', SMOTE(random_state=42)),
        ('classifier', GradientBoostingClassifier(
            n_estimators=120,
            learning_rate=0.08,
            max_depth=5,
            subsample=0.85,
            random_state=42
        ))
    ])

    print("Training GradientBoostingClassifier with SMOTE class balancing...")
    pipeline.fit(X_train, y_train)

    # Predictions & Evaluation
    y_pred_proba = pipeline.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.50).astype(int)

    auc = roc_auc_score(y_test, y_pred_proba)
    precision, recall, f1, _ = precision_recall_fscore_support(y_test, y_pred, average='binary')
    cm = confusion_matrix(y_test, y_pred).tolist()

    print("\n================ MODEL EVALUATION REPORT ================")
    print(f"ROC-AUC Score: {auc:.4f}")
    print(f"Precision: {precision:.4f}")
    print(f"Recall: {recall:.4f}")
    print(f"F1-Score: {f1:.4f}")
    print(f"Confusion Matrix: {cm}")
    print("\nDetailed Classification Report:")
    print(classification_report(y_test, y_pred))
    print("========================================================\n")

    # Save trained pipeline model
    model_path = os.path.join(data_dir, 'model.joblib')
    joblib.dump(pipeline, model_path)
    print(f"Saved model pipeline to: {model_path}")

    # Feature names extraction for explainability
    ohe = pipeline.named_steps['preprocessor'].named_transformers_['cat']
    cat_feature_names = ohe.get_feature_names_out(categorical_features).tolist()
    all_transformed_features = cat_feature_names + numeric_features

    # Feature Importance analysis
    gb_model = pipeline.named_steps['classifier']
    importances = gb_model.feature_importances_.tolist()
    feat_imp = sorted(zip(all_transformed_features, importances), key=lambda x: x[1], reverse=True)

    metrics_dict = {
        "roc_auc": float(round(auc, 4)),
        "precision": float(round(precision, 4)),
        "recall": float(round(recall, 4)),
        "f1_score": float(round(f1, 4)),
        "confusion_matrix": cm,
        "imbalance_handling": "SMOTE (Synthetic Minority Over-sampling Technique)",
        "categorical_features": categorical_features,
        "numeric_features": numeric_features,
        "transformed_features": all_transformed_features,
        "top_feature_importances": [{"feature": f, "importance": round(imp, 4)} for f, imp in feat_imp[:10]]
    }

    metrics_path = os.path.join(data_dir, 'model_metrics.json')
    with open(metrics_path, 'w') as f:
        json.dump(metrics_dict, f, indent=2)

    print(f"Saved evaluation metrics & feature metadata to: {metrics_path}")

if __name__ == '__main__':
    train_conversion_model()
