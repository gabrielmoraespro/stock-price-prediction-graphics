import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
import plotly.express as px
import plotly.graph_objects as go
from ta.volatility import BollingerBands
from ta.trend import MACD, EMAIndicator, SMAIndicator
from ta.momentum import RSIIndicator
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.neighbors import KNeighborsRegressor
from xgboost import XGBRegressor
from sklearn.metrics import r2_score, mean_absolute_error

# Configuração do layout
st.set_page_config(page_title="Stock Price Predictions", layout="wide")

st.title('📈 Stock Price Predictions')
st.sidebar.info("Created and designed by [Vikas Sharma](https://www.linkedin.com/in/vikas-sharma005/)")

@st.cache_data
def download_data(symbol, start_date, end_date):
    """Baixa os dados do Yahoo Finance e ajusta as colunas."""
    try:
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        if df.empty:
            st.error("⚠️ No data found for the given stock symbol and date range.")
            return None
        
        # Resetar o índice para garantir que a coluna 'Date' esteja disponível
        df.reset_index(inplace=True)

        # Se houver MultiIndex, transformamos em colunas simples
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(col).strip() for col in df.columns]  # Flatten MultiIndex
        
        # Renomeia as colunas removendo o nome do ticker se presente
        df.columns = [col.split('_')[0] if '_' in col else col for col in df.columns]
        
        return df
    except Exception as e:
        st.error(f"❌ Error downloading data: {e}")
        return None

def plot_chart(df, title, y_column, color="blue"):
    """Gera gráficos interativos usando Plotly."""
    df = df.copy()
    df = df.reset_index()  # Garantindo que não há MultiIndex

    # Confirma se a coluna esperada existe
    if y_column not in df.columns:
        st.error(f"⚠️ Column '{y_column}' not found in DataFrame. Available columns: {df.columns.tolist()}")
        return

    fig = px.line(df, x="Date", y=y_column, title=title)
    fig.update_traces(line=dict(color=color))
    st.plotly_chart(fig, use_container_width=True)


def tech_indicators(df):
    """Exibe indicadores técnicos."""
    st.header('📊 Technical Indicators')
    option = st.radio('Choose a Technical Indicator:', ['Close', 'Bollinger Bands', 'MACD', 'RSI', 'SMA', 'EMA'])

    if 'Close' not in df.columns:
        st.error("⚠️ Data does not contain 'Close' prices.")
        return

    try:
        close_prices = df['Close'].squeeze()  # Garante que os dados são 1D

        df['bb_high'] = BollingerBands(close_prices).bollinger_hband()
        df['bb_low'] = BollingerBands(close_prices).bollinger_lband()
        df['macd'] = MACD(close_prices).macd()
        df['rsi'] = RSIIndicator(close_prices).rsi()
        df['sma'] = SMAIndicator(close_prices, window=14).sma_indicator()
        df['ema'] = EMAIndicator(close_prices).ema_indicator()
    except Exception as e:
        st.error(f"❌ Error calculating indicators: {e}")
        return

    if option == 'Close':
        plot_chart(df, 'Close Price', 'Close')
    elif option == 'Bollinger Bands':
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close Price'))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_high'], mode='lines', name='Upper Band', line=dict(dash='dot')))
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_low'], mode='lines', name='Lower Band', line=dict(dash='dot')))
        st.plotly_chart(fig, use_container_width=True)
    elif option == 'MACD':
        plot_chart(df, 'MACD', 'macd', color="red")
    elif option == 'RSI':
        plot_chart(df, 'RSI (Relative Strength Index)', 'rsi', color="purple")
    elif option == 'SMA':
        plot_chart(df, 'Simple Moving Average', 'sma', color="orange")
    else:
        plot_chart(df, 'Exponential Moving Average', 'ema', color="green")

def dataframe(df):
    """Exibe os dados recentes."""
    st.header('📄 Recent Data')
    st.dataframe(df.tail(10))

def predict(df):
    """Faz previsões de preços."""
    st.header('🔮 Price Prediction')
    model_choice = st.selectbox('Choose a model:', ['Linear Regression', 'Random Forest', 'Extra Trees', 'KNN', 'XGBoost'])
    days_forecast = st.slider('How many days to predict?', 1, 30, 5)

    if st.button('Predict'):
        model_dict = {
            'Linear Regression': LinearRegression(),
            'Random Forest': RandomForestRegressor(),
            'Extra Trees': ExtraTreesRegressor(),
            'KNN': KNeighborsRegressor(),
            'XGBoost': XGBRegressor()
        }
        train_and_predict(model_dict[model_choice], df, days_forecast)

def train_and_predict(model, df, days):
    """Treina o modelo e faz previsões."""
    df = df[['Close']].copy()
    df['Target'] = df['Close'].shift(-days)

    if df['Target'].isnull().all():
        st.error("⚠️ Not enough data to make predictions.")
        return

    X = df.dropna().drop(columns=['Target']).values
    y = df.dropna()['Target'].values

    scaler = StandardScaler()
    X = scaler.fit_transform(X)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    st.subheader("📊 Model Performance")
    st.write(f"**R² Score:** {r2_score(y_test, preds):.2f}")
    st.write(f"**Mean Absolute Error:** {mean_absolute_error(y_test, preds):.2f}")

    st.subheader("📈 Future Predictions")
    future_preds = model.predict(scaler.transform(df[['Close']].values[-days:]))
    forecast_df = pd.DataFrame({"Day": range(1, days + 1), "Predicted Price": future_preds})
    st.dataframe(forecast_df)

def main():
    """Controle do aplicativo Streamlit."""
    option = st.sidebar.selectbox('Select an option', ['Visualize', 'Recent Data', 'Predict'])
    stock_symbol = st.sidebar.text_input('Enter Stock Symbol', 'AAPL').upper()
    
    today = datetime.date.today()
    duration = st.sidebar.number_input('Select duration (days)', value=365, min_value=30)
    start_date = st.sidebar.date_input('Start Date', today - datetime.timedelta(days=duration))
    end_date = st.sidebar.date_input('End Date', today)

    if st.sidebar.button('Load Data'):
        if start_date < end_date:
            st.sidebar.success(f'Start: `{start_date}`\nEnd: `{end_date}`')
            df = download_data(stock_symbol, start_date, end_date)

            if df is not None:
                if option == 'Visualize':
                    tech_indicators(df)
                elif option == 'Recent Data':
                    dataframe(df)
                else:
                    predict(df)
        else:
            st.sidebar.error("⚠️ End date must be after start date.")

if __name__ == '__main__':
    main()

