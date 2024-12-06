import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
import plotly.express as px

def perform_churn_analysis(merged, households, churn_threshold=6):
    try:
        # Convert 'purchase_' column to datetime
        merged['purchase_'] = pd.to_datetime(merged['purchase_'], errors='coerce')  # Convert to datetime format
        if merged['purchase_'].isnull().any():
            print("Warning: Some 'purchase_' dates could not be parsed and will be excluded.")

        # Drop rows with invalid or missing dates
        merged = merged.dropna(subset=['purchase_'])

        # Calculate the latest purchase date
        latest_date = merged['purchase_'].max()

        # Calculate recency (days since last purchase)
        merged['recency'] = (latest_date - merged['purchase_']).dt.days

        # Create RFM table
        rfm = merged.groupby('hshd_num').agg({
            'recency': 'min',
            'basket_num': 'nunique',
            'spend': 'sum'
        }).reset_index()

        # Label churn
        rfm['churn'] = (rfm['recency'] > churn_threshold * 30).astype(int)

        # Merge with household data
        rfm = rfm.merge(households, on='hshd_num', how='left')

        # Feature selection
        X = rfm[['recency', 'basket_num', 'spend']]
        y = rfm['churn']

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        # Train Random Forest
        clf = RandomForestClassifier(random_state=42)
        clf.fit(X_train, y_train)

        # Predict churn probabilities
        rfm['churn_probability'] = clf.predict_proba(X)[:, 1]

        # Scatter plot visualization
        fig = px.scatter(
            rfm, x='recency', y='spend', color='churn',
            title="Customer Churn Analysis",
            labels={'recency': 'Days Since Last Purchase', 'spend': 'Total Spend'},
            hover_data=['hshd_num', 'churn_probability']
        )

        return fig.to_html(full_html=False), None
    except Exception as e:
        return None, f"An error occurred during churn analysis: {e}"
