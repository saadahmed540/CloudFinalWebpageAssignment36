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

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        try:
            if not request.files:
                return "No files uploaded. Please upload at least one file."
            conn = pyodbc.connect(DB_CONNECTION_STRING)
            cursor = conn.cursor()
            # Process files
            files_to_process = {
                'households_file': ('Households', households, [
                    'hshd_num', 'loyalty_flag', 'age_range', 'marital_status',
                    'income_range', 'homeowner_flag', 'household_composition', 'hh_size', 'children'
                ]),
                'transactions_file': ('Transactions', transactions, [
                    'hshd_num', 'basket_num', 'date', 'product_num', 'spend', 'units', 'region'
                ]),
                'products_file': ('Products', products, [
                    'product_num', 'department', 'commodity', 'brand_type', 'natural_organic'
                ]),
            }
            for file_key, (table_name, df, required_columns) in files_to_process.items():
                if file_key in request.files:
                    file = request.files[file_key]
                    new_df = pd.read_csv(file)
                    new_df = normalize_columns(new_df)
                    if not set(required_columns).issubset(new_df.columns):
                        return f"Missing required columns in {table_name}.csv."
                    # Insert into database logic...
            conn.commit()
            conn.close()
            return redirect(url_for('search'))
        except Exception as e:
            return f"An error occurred while uploading data: {e}"
    return render_template('upload.html')

# Load datasets
households = pd.read_csv('400_households.csv')
transactions = pd.read_csv('400_transactions.csv')
products = pd.read_csv('400_products.csv')

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
    basket_data = merged.groupby(['hshd_num', 'basket_num'])['commodity'].apply(list).reset_index()
    basket_data['commodity'] = basket_data['commodity'].apply(lambda x: ', '.join(x))
    fig = px.bar(
        basket_data.head(10),
        x='hshd_num', y='commodity', title='Top 10 Basket Combinations'
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
