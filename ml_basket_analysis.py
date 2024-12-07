import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score
from sklearn.preprocessing import MultiLabelBinarizer
import plotly.express as px

def perform_basket_analysis(merged, target_item):
    if merged.empty:
        return None, "Merged data is unavailable."
 
    try:
        # Prepare basket data
        basket_data = merged.copy()
        basket_data['commodity'] = basket_data['commodity'].str.strip()  # Remove trailing spaces
        basket_data = basket_data.groupby('basket_num')['commodity'].apply(list).reset_index()

        # One-hot encode commodities
        mlb = MultiLabelBinarizer()
        basket_encoded = pd.DataFrame(mlb.fit_transform(basket_data['commodity']), columns=mlb.classes_, index=basket_data.index)
        basket_encoded['basket_num'] = basket_data['basket_num']

        # Check if target item exists
        if target_item not in basket_encoded.columns:
            return None, f"Target item '{target_item}' not found in data. Available items: {', '.join(mlb.classes_)}"

        basket_encoded[target_item] = basket_encoded[target_item].astype(int)

        # Split data into features and target
        X = basket_encoded.drop(columns=['basket_num', target_item])
        y = basket_encoded[target_item]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Gradient Boosting Classifier
        model = GradientBoostingClassifier(random_state=42)
        model.fit(X_train, y_train)

        # Predict and evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Feature importance analysis
        feature_importance = pd.Series(model.feature_importances_, index=X.columns)
        important_features = feature_importance.nlargest(10)

        # Plot feature importance
        fig = px.bar(
            important_features.sort_values(),
            orientation='h',
            title=f"Top 10 Products Associated with '{target_item}'",
            labels={"value": "Importance Score", "index": "Product"}
        )

        return fig.to_html(full_html=False), None
    except Exception as e:
        return None, f"An error occurred: {e}"
