import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from prophet import Prophet
from io import BytesIO

st.set_page_config(page_title = "Retail Analytics Dashboard",
                   page_icon = "logo.ico",
                   layout="wide"    #using full screen instead of center
                )

@st.cache_data
def get_branch_coordinates():
    # Map cities to their coordinates (replace with your actual branch locations)
    return {
        "Yangon": (16.8409, 96.1735),
        "Naypyitaw": (19.7633, 96.0785),
        "Mandalay": (21.9588, 96.0891)
    }

def get_data_from_excel():
    df = pd.read_excel(
        io = 'supermarkt_sales.xlsx',
        engine = 'openpyxl',
        sheet_name= 'Sales',
        skiprows= 3,
        usecols= 'B:R',
        nrows= 1000
    )
    df['Date'] = pd.to_datetime(df['Date'])
    df['hour'] = pd.to_datetime(df['Time'], format="%H:%M:%S").dt.hour  # Add 'hour' column to dataframe

    coordinates = {
        "Yangon": (16.8409, 96.1735),
        "Naypyitaw": (19.7633, 96.0785),
        "Mandalay": (21.9588, 96.0891)
    }
    coordinates = get_branch_coordinates()
    df['lat'] = df['City'].map(lambda x: coordinates.get(x, (None, None))[0])
    df['lon'] = df['City'].map(lambda x: coordinates.get(x, (None, None))[1])

    return df

#st.dataframe(df)
df = get_data_from_excel()

def has_enough_data(df, min_rows=2):
    """Returns True if DataFrame has at least min_rows non-NaN rows."""
    return df.dropna().shape[0] >= min_rows

def convert_df_to_csv(df):
    return df.to_csv(index=False).encode("utf-8")

animation_settings = dict(
    transition=dict(duration=800, easing='cubic-in-out')
)

if 'previous_filters' not in st.session_state:
    st.session_state.previous_filters = {
        'city': [],
        'customer_type': [],
        'gender': [],
        'date_range': (None, None)
    }

# ---- Sidebar ----
st.sidebar.image("logo.png", width=50)
st.sidebar.header("Please Filter Here:")

min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

# Add reset button at the top of filters
if st.sidebar.button("🔄 Reset All Filters"):
    # Reset all filter widgets to default values
    st.session_state.city_filter = df["City"].unique().tolist()
    st.session_state.customer_type_filter = df["Customer_type"].unique().tolist()
    st.session_state.gender_filter = df["Gender"].unique().tolist()
    st.session_state.date_filter = (df['Date'].min().date(), df['Date'].max().date())
    st.session_state.update({
        'city_filter': df["City"].unique().tolist(),
        'customer_type_filter': df["Customer_type"].unique().tolist(),
        'gender_filter': df["Gender"].unique().tolist(),
        'date_filter': (min_date, max_date)
    })
    st.rerun()

city = st.sidebar.multiselect(
    "Select the City:",
    options=df["City"].unique().tolist(),
    default=st.session_state.get("city_filter", df["City"].unique().tolist()),
    key='city_filter'
)

customer_type = st.sidebar.multiselect(
    "Select the Customer Type:",
    options=df["Customer_type"].unique().tolist(),
    default=st.session_state.get("customer_type_filter", df["Customer_type"].unique().tolist()),
    key='customer_type_filter'
)

gender = st.sidebar.multiselect(
    "Select the Gender:",
    options=df["Gender"].unique().tolist(),
    default=st.session_state.get("gender_filter", df["Gender"].unique().tolist()),
    key='gender_filter'
)

date_selection = st.sidebar.date_input(
    "Select Date Range:",
    value=st.session_state.get("date_filter", (min_date, max_date)),
    min_value=min_date,
    max_value=max_date,
    key='date_filter'
)

st.sidebar.markdown("---")
st.sidebar.header("Export Data")

# Handle partial/incorrect selections
if isinstance(date_selection, tuple) and len(date_selection) == 2:
    from_date, to_date = date_selection
else:
    from_date = to_date = min_date  # Fallback to full range

# Convert to pandas-compatible datetime
from_date_pd = pd.to_datetime(from_date)
to_date_pd = pd.to_datetime(to_date)

current_filters = {
    'city': city,
    'customer_type': customer_type,
    'gender': gender,
    'date_range': (from_date, to_date)
}
filters_changed = current_filters != st.session_state.previous_filters
st.session_state.previous_filters = current_filters

df_selection = df.query(
    "City == @city & Customer_type == @customer_type & Gender == @gender"
)

df_selection = df_selection[
    (df_selection['Date'] >= pd.to_datetime(from_date)) &
    (df_selection['Date'] <= pd.to_datetime(to_date))
]


if not df_selection.empty:
    # CSV Download
    csv = df_selection.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        "⬇️ Download as CSV",
        data=csv,
        file_name='filtered_data.csv',
        mime='text/csv',
        help="Download filtered data in CSV format"
    )
    
    # Excel Download
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
        df_selection.to_excel(writer, index=False, sheet_name='FilteredData')
    excel_buffer.seek(0)
    st.sidebar.download_button(
        "⬇️ Download as Excel",
        data=excel_buffer,
        file_name='filtered_data.xlsx',
        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        help="Download filtered data in Excel format"
    )
else:
    st.sidebar.warning("No data available for download with current filters")

# ---- Main Page ---- 

st.markdown("""
<h1 style="margin-bottom: 0; color: #0083B8;">
    <img src="https://img.icons8.com/?size=100&id=7DajRjkNMHR5&format=png&color=000000" width="40">
    Retail Analytics Dashboard
</h1>
""", unsafe_allow_html=True)

st.markdown("##")

# TOP KPI's
if not df_selection.empty:
    total_sales = int(df_selection["Total"].sum())
    average_rating = round(df_selection["Rating"].mean(), 1)
    star_rating = ":star:" * int(round(average_rating, 0))
    average_sale_by_transaction = round(df_selection["Total"].mean(), 2)
    gross_profit = df_selection["gross income"].sum()
    margin_percentage = df_selection["gross margin percentage"].mean()
else:
    # Set default values when no data
    total_sales = 0
    average_rating = 0.0
    star_rating = ""
    average_sale_by_transaction = 0.0
    gross_profit = 0.0
    margin_percentage = 0.0

#KPI columns section:
left_column, middle_column, right_column = st.columns(3)
with left_column:
    st.subheader("Total Sales:")
    st.subheader(f"US $ {total_sales:,}")
with middle_column: 
    st.subheader("Average Rating:")
    st.subheader(f"{average_rating} {star_rating}")
with right_column:
    st.subheader("Average Sales Per Transaction:")
    st.subheader(f"US $ {average_sale_by_transaction}") 

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Gross Profit")
    st.markdown(f"<h2 style='color:#0083B8'>US $ {gross_profit:,.2f}</h2>", 
               unsafe_allow_html=True)

with col2:
    st.markdown("### Avg Margin %")
    st.markdown(f"<h2 style='color:#0083B8'>{margin_percentage:.1f}%</h2>", 
               unsafe_allow_html=True)

st.markdown("---")

# Unified chart layout configuration
chart_layout = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=20, r=20, t=60, b=20),
    height=400,
    **animation_settings
)

# SALES BY PRODUCT LINE [BAR CHART]
sales_by_product_line = (
    df_selection.groupby(by=["Product line"])[["Total"]].sum().sort_values(by="Total")
)
fig_product_sales = px.bar(
    sales_by_product_line,
    x = "Total",
    y = sales_by_product_line.index,
    orientation = "h",
    title = "<b>Sales By Product Line</b>",
    color_discrete_sequence= ["#0083B8"] * len(sales_by_product_line),
    template = "plotly_white"
)
fig_product_sales.update_layout(
    xaxis=dict(showgrid=False),
    **chart_layout
)

# SALES BY HOUR [BAR CHART]

sales_by_hour = df_selection.groupby(by=["hour"])[["Total"]].sum()
fig_hourly_sales = px.bar(
    sales_by_hour,
    x = sales_by_hour.index,
    y = "Total",
    title = "<b>Sales By Hour</b>",
    color_discrete_sequence= ["#0083B8"] * len(sales_by_hour),
    template = "plotly_white"
)

fig_hourly_sales.update_layout(
    xaxis=dict(tickmode="linear", showgrid=False),
    yaxis=dict(showgrid=False),
    **chart_layout
)

# ---- Sales Trend Over Time ----
sales_trend = (
    df_selection.groupby('Date')[['Total']].sum().reset_index()
)
fig_sales_trend = px.line(
    sales_trend,
    x='Date',
    y='Total',
    title='<b>Sales Trend Over Time</b>',
    markers=True,
    template='plotly_white'
)

fig_sales_trend.update_traces(line=dict(width=3), marker=dict(size=6))
fig_sales_trend.update_layout(
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False),
    **chart_layout
)

# ---- GEOGRAPHICAL VISUALIZATION ----

# Aggregate data by branch
branch_sales = df_selection.groupby('City').agg({
    'Total': 'sum',
    'Rating': 'mean',
    'lat': 'first',
    'lon': 'first'
}).reset_index()


# Create the map
fig_map = px.scatter_mapbox(
    branch_sales,
    lat="lat",
    lon="lon",
    color="Total",
    size="Total",
    color_continuous_scale=px.colors.sequential.Cividis,
    size_max=20,
    zoom=5,
    hover_name="City",
    hover_data={
        "Total": ":.2f",
        "Rating": ":.2f",
        "lat": False,
        "lon": False
    },
    title="<b>Sales by Branch Location</b>"
)

fig_map.update_layout(
    mapbox_style="carto-positron",
    margin={"r":0,"t":40,"l":0,"b":0},
    height=400,
    **animation_settings
)

# ---- Profit Margin Visualization ----
profit_trend = df_selection.groupby('Date')[['gross income']].sum().reset_index()
fig_profit_trend = px.area(
    profit_trend,
    x='Date',
    y='gross income',
    title='<b>Profit Trend Over Time</b>',
    template='plotly_white'
)
fig_profit_trend.update_layout(
    xaxis=dict(showgrid=False),
    yaxis=dict(showgrid=False),
    **chart_layout
)

# ---- Forecasting ----
forecast_ready = has_enough_data(sales_trend, min_rows=2)
if forecast_ready:
    forecast_df = sales_trend.rename(columns={'Date': 'ds', 'Total': 'y'})
    m = Prophet(daily_seasonality=True)
    m.fit(forecast_df)
    future = m.make_future_dataframe(periods=30)
    forecast = m.predict(future)
    fig_forecast = px.line(
        forecast, x='ds', y='yhat', 
        title='<b>Sales Forecast (Prophet Model)</b>',
        template='plotly_white'
    )
    fig_forecast.add_scatter(x=forecast_df['ds'], y=forecast_df['y'], mode='markers', name='Actual Sales')
    fig_forecast.update_layout(
        xaxis_title="Date",
        yaxis_title="Sales",
        plot_bgcolor="rgba(0,0,0,0)",
        transition=dict(duration=800, easing='cubic-in-out')
    )
else:
    fig_forecast = None

# ---- Anomaly Detection ----
anomaly_ready = has_enough_data(sales_trend, min_rows=2)
if anomaly_ready:
    sales_trend['zscore'] = (sales_trend['Total'] - sales_trend['Total'].mean()) / sales_trend['Total'].std()
    threshold = 2
    sales_trend['anomaly'] = sales_trend['zscore'].abs() > threshold
    fig_anomaly = px.scatter(
        sales_trend, x='Date', y='Total',
        color='anomaly',
        color_discrete_map={True: 'red', False: '#0083B8'},
        title='<b>Sales Anomalies</b>',
        template='plotly_white'
    )
    fig_anomaly.update_traces(marker=dict(size=10))
    fig_anomaly.update_layout(
        xaxis_title="Date",
        yaxis_title="Sales",
        plot_bgcolor="rgba(0,0,0,0)",
        transition=dict(duration=800, easing='cubic-in-out')
    )
else:
    fig_anomaly = None

# ---- Display Charts ----
st.markdown("##")

tab1, tab2, tab3, tab4, tab5  = st.tabs(["📊 Sales Overview", "💰 Profit Analysis", "📈 Trends", "🔮 Predictive Analytics" ,"📍 Locations"])

with tab1:
    st.markdown("<h2 style='color:#0083B8'>Sales Overview</h2>", unsafe_allow_html=True)
    st.markdown("This section provides insights into sales performance across different product lines and hours of operation.") 

    with st.container():
        st.plotly_chart(fig_product_sales, use_container_width=True)

    with st.container():
        st.plotly_chart(fig_hourly_sales, use_container_width=True)

with tab2:
    st.markdown("<h2 style='color:#0083B8'>Profit Analysis</h2>", unsafe_allow_html=True)
    st.markdown("This section provides insights into profit trends over time.")

    with st.container():
        st.plotly_chart(fig_profit_trend, use_container_width=True)

with tab3:
    st.markdown("<h2 style='color:#0083B8'>Sales Trends</h2>", unsafe_allow_html=True)
    st.markdown("This section provides insights into sales trends over time.")

    with st.container():
        st.plotly_chart(fig_sales_trend, use_container_width=True)

with tab4:
    st.markdown("<h2 style='color:#0083B8'>Predictive Analytics</h2>", unsafe_allow_html=True)
    st.markdown("This section provides insights into sales forecasting and anomaly detection.")

    st.markdown("### Sales Forecast (Next 30 Days)")

    if fig_forecast:
        with st.container():
            st.plotly_chart(fig_forecast, use_container_width=True)
    else:
        st.info("Not enough data to generate a forecast. Please select a broader date range or more filters.")

    st.markdown("### Anomaly Detection")
    if fig_anomaly:
        with st.container():
            st.plotly_chart(fig_anomaly, use_container_width=True)
    else:
        st.info("Not enough data to detect anomalies. Please select a broader date range or more filters.")


with tab5:
    st.markdown("<h2 style='color:#0083B8'>Locations</h2>", unsafe_allow_html=True)
    with st.container():
        st.plotly_chart(fig_map, use_container_width=True)

# # ---- Header ----
# st.markdown("""
# <style>
#     .name-corner {
#         position: fixed;
#         top: 10px;
#         right: 20px;
#         font-size: 16px;
#         color: #F0FFFF;
#         z-index: 1000;
#     }
# </style>

# <div class="name-corner">Created by Amjad Ali</div>
# """, unsafe_allow_html=True)

# ---- Hide Streamlit Style ----

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html= True)

# ---- Footer ----

st.markdown("""
<style>
.footer {
    position: fixed;
    left: 0;
    bottom: 0;
    width: 100%;
    background: rgba(0,131,184,0.05);
    color: #0083B8;
    text-align: right;
    padding: 8px 16px;
    font-size: 14px;
    z-index: 999;
}
</style>
<div class="footer">
    &copy; 2024 Amjad Ali | Powered by Streamlit
</div>
""", unsafe_allow_html=True)
