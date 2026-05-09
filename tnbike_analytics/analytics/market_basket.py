"""
Phân tích giỏ hàng — Đại lý thường đặt kết hợp những nhóm xe nào?
Dùng Apriori (mlxtend). Cột: so_number, group_code/line_name, quantity.
"""
import pandas as pd


def build_basket(df: pd.DataFrame, by: str = "group_code") -> pd.DataFrame:
    """Ma trận one-hot: hàng = đơn hàng, cột = nhóm SP."""
    basket = df.groupby(["so_number", by])["quantity"].sum().unstack().fillna(0)
    return (basket > 0).astype(bool)


def run_apriori(basket: pd.DataFrame, min_support: float = 0.05, min_confidence: float = 0.3):
    """Chạy Apriori và trả về association rules."""
    from mlxtend.frequent_patterns import apriori, association_rules
    frequent = apriori(basket, min_support=min_support, use_colnames=True)
    rules = association_rules(frequent, metric="confidence", min_threshold=min_confidence)
    rules = rules.sort_values("lift", ascending=False)
    rules["antecedents_str"] = rules["antecedents"].apply(lambda x: " + ".join(sorted(x)))
    rules["consequents_str"] = rules["consequents"].apply(lambda x: " + ".join(sorted(x)))
    return rules[["antecedents_str", "consequents_str", "support", "confidence", "lift"]]


def co_purchase_heatmap(df: pd.DataFrame, by: str = "group_code") -> pd.DataFrame:
    """Ma trận đồng mua hàng: cặp nhóm SP xuất hiện cùng trong bao nhiêu đơn."""
    basket = build_basket(df, by)
    return basket.T.dot(basket).astype(int)
