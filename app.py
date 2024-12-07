from flask import Flask, request, render_template, redirect, url_for
import pyodbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ml_basket_analysis import perform_basket_analysis
from churn_prediction import perform_churn_analysis
from ml_basket_analysis import perform_basket_analysis


app = Flask(__name__)

# Database connection details
DB_CONNECTION_STRING = (
    'Driver={ODBC Driver 17 for SQL Server};'
    'Server=finalcloudassignment36.database.windows.net;'
    'Database=RetailDB;'
    'UID=retaildb;'
    'PWD=Shawarma@540;'
)

# Normalize column names
def normalize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df

valid_username = "admin"
valid_password = "password123"
valid_email = "admin@example.com"

@app.route('/')
def index():
    return render_template('index.html')  # Render the HTML form

@app.route('/submit', methods=['POST'])
def submit():
    username = request.form.get('username')
    password = request.form.get('password')
    email = request.form.get('email')

    # Check if the details are correct
    if username == valid_username and password == valid_password and email == valid_email:
        return redirect(url_for('dashboard'))  # Redirect to dashboard page if credentials are correct
    else:
        return render_template('index.html', error_message="Invalid credentials, please try again.")

@app.route('/logout')
def logout():
    session.clear()  # Clear the session
    return redirect(url_for('index'))  # Redirect to the login or home page

# Search Endpoint
@app.route('/search', methods=['GET', 'POST'])
def search():
    results = []
    hshd_num = None
    if request.method == 'POST':
        hshd_num = request.form.get('hshd_num')
        if hshd_num:
            try:
                conn = pyodbc.connect(DB_CONNECTION_STRING)
                cursor = conn.cursor()
                query = """
                    SELECT 
                        T.Hshd_num, T.Basket_num, T.Date, T.Product_num,
                        P.Department, P.Commodity
                    FROM Transactions T
                    JOIN Products P ON T.Product_num = P.Product_num
                    WHERE T.Hshd_num = ?
                    ORDER BY T.Hshd_num, T.Basket_num, T.Date, T.Product_num, P.Department, P.Commodity;
                """
                cursor.execute(query, hshd_num)
                results = cursor.fetchall()
                conn.close()
            except Exception as e:
                return f"An error occurred: {e}"
    return render_template('search.html', results=results, hshd_num=hshd_num)

# Data Loading Web App
@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        try:
            # Check if files are uploaded
            if not request.files:
                return "No files uploaded. Please upload at least one file."

            conn = pyodbc.connect(DB_CONNECTION_STRING)
            cursor = conn.cursor()

            # Process Households.csv
            if 'households_file' in request.files:
                households_file = request.files['households_file']
                households_df = pd.read_csv(households_file)

                # Normalize column names
                households_df.columns = households_df.columns.str.strip().str.lower()

                # Clean numeric columns (e.g., 'hh_size', 'children')
                households_df['hh_size'] = pd.to_numeric(households_df['hh_size'], errors='coerce')
                households_df['children'] = pd.to_numeric(households_df['children'], errors='coerce')

                # Check for missing or invalid values
                if households_df[['hh_size', 'children']].isnull().any().any():
                    return "Invalid numeric values in Households.csv. Please check your data."

                for _, row in households_df.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO Households (Hshd_num, Loyalty_flag, Age_range, Marital_status, Income_range,
                                                Homeowner_flag, Household_composition, HH_size, Children)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        row['hshd_num'], row['l'], row['age_range'], row['marital'],
                        row['income_range'], row['homeowner'], row['hshd_composition'], row['hh_size'], row['children']
                    )


            # Process Households.csv
            # if 'households_file' in request.files:
            #     households_file = request.files['households_file']
            #     households_df = pd.read_csv(households_file)

            #     # Normalize column names to lowercase
            #     households_df.columns = households_df.columns.str.strip().str.lower()

            #     # Verify required columns exist
            #     required_columns = [
            #         'hshd_num', 'l', 'age_range', 'marital',
            #         'income_range', 'homeowner', 'hshd_composition', 'hh_size', 'children'
            #     ]
            #     if not set(required_columns).issubset(households_df.columns):
            #         return "Missing required columns in Households.csv."

            #     for _, row in households_df.iterrows():
            #         cursor.execute(
            #             """
            #             INSERT INTO Households (Hshd_num, Loyalty_flag, Age_range, Marital_status, Income_range, Homeowner_flag, Household_composition, HH_size, Children)
            #             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            #             """,
            #             row['hshd_num'], row['l'], row['age_range'], row['marital'],
            #             row['income_range'], row['homeowner'], row['hshd_composition'], row['hh_size'], row['children']
            #         )

            # Process Transactions.csv
            if 'transactions_file' in request.files:
                transactions_file = request.files['transactions_file']
                transactions_df = pd.read_csv(transactions_file)

                # Normalize column names to lowercase
                transactions_df.columns = transactions_df.columns.str.strip().str.lower()

                # Verify required columns exist
                required_columns = [
                    'basket_num', 'hshd_num', 'purchase_', 'product_num', 'spend', 'units', 'store_r','week_num','year'
                ]
                if not set(required_columns).issubset(transactions_df.columns):
                    return "Missing required columns in Transactions.csv."

                for _, row in transactions_df.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO Transactions (Basket_num, Hshd_num, Date, Product_num, Spend, Units, Store_region, Week_num, Year)
                        VALUES (?, ?, ?, ?, ?, ?, ?,?,?)
                        """,
                        row['basket_num'], row['hshd_num'],row['purchase_'], row['product_num'],
                        row['spend'], row['units'], row['store_r'],row['week_num'], row['year']
                    )

            # Process Products.csv
            if 'products_file' in request.files:
                products_file = request.files['products_file']
                products_df = pd.read_csv(products_file)

                # Normalize column names to lowercase
                products_df.columns = products_df.columns.str.strip().str.lower()

                # Verify required columns exist
                required_columns = [
                    'product_num', 'department', 'commodity', 'brand_ty', 'natural_organic_flag'
                ]
                if not set(required_columns).issubset(products_df.columns):
                    return "Missing required columns in Products.csv."

                for _, row in products_df.iterrows():
                    cursor.execute(
                        """
                        INSERT INTO Products (Product_num, Department, Commodity, Brand_type, Natural_organic_flag)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        row['product_num'], row['department'], row['commodity'], row['brand_ty'], row['natural_organic_flag']
                    )

            # Commit changes and close connection
            conn.commit()
            conn.close()

            # Redirect to the search page after successful upload
            return redirect(url_for('search_data'))

        except Exception as e:
            return f"An error occurred while uploading data: {e}"

    return render_template('upload.html')

# Load datasets
households = pd.read_csv('https://cloudfinalassignment36.blob.core.windows.net/households/400_households.csv')
transactions = pd.read_csv('https://cloudfinalassignment36.blob.core.windows.net/transactions/400_transactions.csv')
products = pd.read_csv('https://cloudfinalassignment36.blob.core.windows.net/products/400_products.csv')

# Standardize column names
transactions.columns = transactions.columns.str.strip().str.lower()
products.columns = products.columns.str.strip().str.lower()
households.columns = households.columns.str.strip().str.lower()

# Merge DataFrames
merged = (
    transactions.merge(products, on='product_num', how='left')
    .merge(households, on='hshd_num', how='left')
)




@app.route('/basket_analysis_ml', methods=['GET', 'POST'])
def basket_analysis_ml():
    try:
        # Get available commodities dynamically from the dataset
        commodities = merged['commodity'].str.strip().unique().tolist()

        # Handle form submission
        if request.method == 'POST':
            target_item = request.form.get('target_item')  # Get selected target item
            if not target_item:
                return "Please select a target item."
            
            fig_html, error = perform_basket_analysis(merged, target_item=target_item)
            if error:
                return error
            return fig_html

        # Render the form for GET requests
        return render_template('basket_analysis_form.html', commodities=commodities)
    except Exception as e:
        return f"An error occurred: {e}"



@app.route('/churn_prediction')
def churn_prediction():
    fig_html, error = perform_churn_analysis(merged, households)
    if error:
        return error
    return fig_html


@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/demographics')
def demographics():
    fig = px.bar(
        households.groupby('hh_size')['hshd_num'].count().reset_index(),
        x='hh_size', y='hshd_num', title='Household Size vs Engagement'
    )
    return fig.to_html()

@app.route('/engagement_over_time')
def engagement_over_time():
    try:
        # Ensure 'purchase_' column is in datetime format
        transactions['purchase_'] = pd.to_datetime(transactions['purchase_'])
        
        # Group by month and calculate monthly spend
        monthly_spend = transactions.groupby(transactions['purchase_'].dt.to_period('M'))['spend'].sum().reset_index()
        
        # Convert Period to string for serialization
        monthly_spend['purchase_'] = monthly_spend['purchase_'].astype(str)
        
        # Create the Plotly figure
        fig = px.line(monthly_spend, x='purchase_', y='spend', title='Engagement Over Time')
        
        # Return the figure as HTML
        return fig.to_html()
    except Exception as e:
        return f"An error occurred: {e}"


@app.route('/basket_analysis')
def basket_analysis():
    # Grouping and summarizing basket data
    basket_data = merged.groupby(['hshd_num', 'basket_num'])['commodity'].apply(list).reset_index()
    basket_data['commodity_count'] = basket_data['commodity'].apply(len)  # Number of items in basket
    basket_data['commodity'] = basket_data['commodity'].apply(lambda x: ', '.join(x))  # Join commodities into a string

    # Sunburst chart with valid soft colors
    fig = px.sunburst(
        basket_data.head(10),
        path=['hshd_num', 'basket_num'],  # Hierarchy: Household -> Basket
        values='commodity_count',  # Basket size (number of items)
        hover_data=['commodity'],  # Display commodities
        title='Top 10 Basket Combinations by Household',
        color='commodity_count',  # Color based on number of items
        color_continuous_scale='blues'  # Use 'blues' for soft colors
    )

    # Simplify layout
    fig.update_layout(
        margin=dict(t=50, l=50, r=50, b=50),
        coloraxis_colorbar=dict(
            title="Number of Items",
            tickprefix="Items: "
        )
    )

    return fig.to_html()

@app.route('/seasonal_trends')
def seasonal_trends():
    transactions['Month'] = pd.to_datetime(transactions['purchase_']).dt.month
    monthly_spend = transactions.groupby('Month')['spend'].sum().reset_index()
    fig = px.bar(monthly_spend, x='Month', y='spend', title='Seasonal Trends in Spending')
    return fig.to_html()

@app.route('/brand_preferences')
def brand_preferences():
    brand_pref = products.groupby('brand_ty')['product_num'].count().reset_index()
    fig = px.pie(brand_pref, names='brand_ty', values='product_num', title='Brand Preferences')
    return fig.to_html()

if __name__ == '__main__':
    app.run(debug=True)
