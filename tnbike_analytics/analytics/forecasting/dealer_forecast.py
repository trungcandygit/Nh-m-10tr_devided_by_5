"""
Dự báo hành vi đại lý — Churn Prediction
Feature engineering từ fact_sales, model: Logistic Regression / Random Forest / GBM
"""
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger("tnbike.forecast.dealer")


def build_dealer_features(df: pd.DataFrame, reference_date=None) -> pd.DataFrame:
    """
    Feature engineering cho churn prediction.
    Features:
    - recency_days, freq_90d, freq_180d, freq_total
    - revenue_90d, revenue_180d, revenue_total, avg_order_value
    - n_product_groups, trend_slope (hướng xu thế doanh thu hàng tháng)
    """
    if reference_date is None:
        reference_date = df["order_date"].max()

    ref  = pd.Timestamp(reference_date)
    d90  = ref - pd.Timedelta(days=90)
    d180 = ref - pd.Timedelta(days=180)

    features = []
    for cust_code, grp in df.groupby("customer_code"):
        grp = grp.sort_values("order_date")
        last_order = grp["order_date"].max()
        recency    = (ref - last_order).days

        grp90  = grp[grp["order_date"] >= d90]
        grp180 = grp[grp["order_date"] >= d180]

        # Xu hướng doanh thu tháng
        monthly_rev = grp.groupby(grp["order_date"].dt.to_period("M"))["line_total"].sum()
        if len(monthly_rev) >= 3:
            x     = np.arange(len(monthly_rev))
            slope = np.polyfit(x, monthly_rev.values, 1)[0]
        else:
            slope = 0.0

        features.append({
            "customer_code":   cust_code,
            "recency_days":    recency,
            "freq_90d":        grp90["so_number"].nunique(),
            "freq_180d":       grp180["so_number"].nunique(),
            "freq_total":      grp["so_number"].nunique(),
            "revenue_90d":     grp90["line_total"].sum(),
            "revenue_180d":    grp180["line_total"].sum(),
            "revenue_total":   grp["line_total"].sum(),
            "avg_order_value": grp.groupby("so_number")["line_total"].sum().mean(),
            "n_product_groups": grp["group_code"].nunique() if "group_code" in grp.columns else 1,
            "trend_slope":     slope,
        })

    return pd.DataFrame(features)


def label_churn(features: pd.DataFrame, inactive_days: int = 90) -> pd.DataFrame:
    """Gán nhãn churn: không mua trong inactive_days ngày = churn = 1."""
    features = features.copy()
    features["churn"] = (features["recency_days"] >= inactive_days).astype(int)
    return features


def train_churn_model(features: pd.DataFrame):
    """
    Train 3 models, chọn model có ROC-AUC cao nhất qua cross-validation.
    Returns: (best_model, scaler, features_with_predictions)
    """
    from sklearn.linear_model      import LogisticRegression
    from sklearn.ensemble          import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.preprocessing     import StandardScaler
    from sklearn.model_selection   import cross_val_score

    X_cols = [
        "recency_days", "freq_90d", "freq_180d", "freq_total",
        "revenue_90d", "revenue_180d", "avg_order_value",
        "n_product_groups", "trend_slope",
    ]
    X = features[X_cols].fillna(0)
    y = features["churn"]

    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    models = {
        "Logistic Regression": LogisticRegression(max_iter=1000),
        "Random Forest":       RandomForestClassifier(n_estimators=100, random_state=42),
        "Gradient Boosting":   GradientBoostingClassifier(random_state=42),
    }

    best_model, best_score = None, 0.0
    for name, model in models.items():
        if len(y.unique()) < 2:
            logger.warning("Chỉ có 1 class trong y — bỏ qua cross-validation")
            best_model = model
            break
        score = cross_val_score(model, X_scaled, y, cv=5, scoring="roc_auc").mean()
        logger.info(f"{name}: ROC-AUC = {score:.3f}")
        if score > best_score:
            best_score = score
            best_model = model

    best_model.fit(X_scaled, y)
    features = features.copy()
    features["churn_prob"] = best_model.predict_proba(X_scaled)[:, 1]
    features["priority"]   = pd.cut(
        features["churn_prob"],
        bins=[0, 0.3, 0.6, 1.0],
        labels=["Thấp", "Trung bình", "Cao"]
    )
    return best_model, scaler, features
