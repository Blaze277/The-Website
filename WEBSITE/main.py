import time
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import json
from flask import Flask, render_template, request, session
import datetime as dt
import requests
from groq import Groq
import os
pio.templates.default = "plotly_dark"
from pathlib import Path
from dotenv import load_dotenv

# Force load from the exact directory of this file
env_path = Path(__file__).resolve().parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)  # override=True ignores any existing env vars

print("DEBUG: Loaded .env from:", env_path)
print("DEBUG: GROQ_API_KEY =", os.getenv("GROQ_API_KEY"))  # Should print your key now

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def kelvin_to_celsius(kelvin):
    return kelvin - 273.15



def safe_download(ticker, retries=2):
    for attempt in range(retries):
        try:
            return yf.download(ticker, period="1y", progress=False)
        except Exception as e:
            print(f"Retry {attempt+1}/{retries} for {ticker}: {e}")
            time.sleep(3)  # wait a sec
    return pd.DataFrame()

def info(ticker,strength,trend):
        prompt = f"""
          You are an  stock bro. Describe {ticker} in 1 small sentence.
          It's showing a {trend} trend with {strength:.1f}% MA crossover strength.
          short and clean and informative adding a tip or smth
          
           
             """
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",  # or "gpt-4o-mini" / whatever fast one you like
                messages=[{"role": "user", "content": prompt}],
                max_tokens=120,
                temperature=0.7  # crank for more chaos
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Roast API fail: {e}")
            return f"Info curently offline, blame Elon: {strength:.1f}% uptrend bro"


expression = ""
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-only-key"
                           )
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/projects", methods=["GET", "POST"])
def projects():
    contents = None
    display = session.get("expression", "0")
    form_type = request.form.get("form_type")
    
    bullish_stocks = []
    graphs_html = []

    print(f"DEBUG: Method={request.method}, form_type={form_type}")  # always log this

    # ---------- WEATHER ----------
    if form_type == "weather" and request.method == "POST":
        CITY = request.form.get("city")

        if CITY:
            BASE_URL = "http://api.openweathermap.org/data/2.5/weather?"
            API_KEY = os.getenv("OPENWEATHER_API_KEY")
            

            url = f"{BASE_URL}appid={API_KEY}&q={CITY}"
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()

                temp_kelvin_max = data["main"]['temp_max']
                temp_celsius_max = kelvin_to_celsius(temp_kelvin_max)
                temp_kelvin_min = data["main"]['temp_min']
                temp_celsius_min = kelvin_to_celsius(temp_kelvin_min)
                feels_like_kelvin = data['main']['feels_like']
                feels_like_celsius = kelvin_to_celsius(feels_like_kelvin)
                description = data['weather'][0]['description']
                humidity = data['main']['humidity']
                sunrise = dt.datetime.fromtimestamp(data['sys']['sunrise']).strftime('%Y-%m-%d %H:%M:%S')
                sunset = dt.datetime.fromtimestamp(data['sys']['sunset']).strftime('%Y-%m-%d %H:%M:%S')
                wind_speed = data['wind']['speed']

                contents = f'''
            City name: {CITY}
            Maximum Temperature: {temp_celsius_max:.2f} °C
            Minimum Temperature: {temp_celsius_min:.2f} °C
            Feels like: {feels_like_celsius:.2f} °C
            Description: {description}
            Humidity: {humidity}%
            Wind Speed: {wind_speed} m/s
            Sunrise: {sunrise}
            Sunset: {sunset}
            '''

    # ---------- CALCULATOR ----------
    elif form_type == "calculator" and request.method == "POST":
        if "expression" not in session:
            session["expression"] = ""

        if "input" in request.form:
            session["expression"] += request.form["input"]

        elif "action" in request.form:
            if request.form["action"] == "clear":
                session["expression"] = ""
            elif request.form["action"] == "equals":
                try:
                    session["expression"] = str(eval(session["expression"]))
                except:
                    session["expression"] = "Error"

        display = session["expression"] or "0"

        
    # ---------- STOCK ROAST ----------
    

    # ---------- FINAL RENDER ----------
    return render_template(
        "project.html",
        content=contents,
        display=display,
        
        form_type=form_type
    )
    # ---------- FINAL RENDER (ALWAYS) ----------
    
@app.route("/stocks", methods=["GET", "POST"])
def stocks():
    form_type = request.form.get("form_type")
    
    bullish_stocks = []
    graphs_html = []

    if form_type == "stocks" and request.method == "POST":
        print("DEBUG: Entered stocks block")
        watchlist = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS",
    "BHARTIARTL.NS", "SBIN.NS", "HINDUNILVR.NS",
    "AXISBANK.NS", "KOTAKBANK.NS", "BAJFINANCE.NS", "MARUTI.NS"]  # small for fast testing
        
        for ticker in watchlist:
            print(f"DEBUG: Starting {ticker}")
            try:
                
                data = yf.download(ticker, period="1y", progress=False)
                time.sleep(4.5)
                print(f"DEBUG: {ticker} - columns: {data.columns.tolist()}")

                # Detect and flatten if MultiIndex (the real fix)
                if isinstance(data.columns, pd.MultiIndex):
                    print(f"DEBUG: MultiIndex detected — extracting {ticker}")
                    # Level 0 = price types ('Close', 'High', etc.)
                    # Level 1 = ticker name
                    if ticker in data.columns.levels[1]:
                        data = data.xs(ticker, level=1, axis=1)
                    else:
                        print(f"DEBUG: Ticker {ticker} not found in MultiIndex levels")
                        continue
                    print(f"DEBUG: After flatten - columns now: {data.columns.tolist()}")

                # Now data should have normal columns: 'Open', 'High', 'Low', 'Close', 'Volume', etc.
                # Proceed with MA calculation
                data['MA50'] = data['Close'].rolling(50).mean()
                data['MA200'] = data['Close'].rolling(200).mean()

                latest = data.iloc[-1]

                # Safe scalar extraction (extra belt & suspenders)
                ma50_val = latest['MA50']
                if isinstance(ma50_val, pd.Series):
                    ma50_val = ma50_val.item()   # grab the single value

                ma200_val = latest['MA200']
                if isinstance(ma200_val, pd.Series):
                    ma200_val = ma200_val.item()

                if pd.isna(ma50_val) or pd.isna(ma200_val):
                    print(f"{ticker}: NaN in MAs — skipping")
                    continue

                print(f"DEBUG: {ticker} - MA50: {ma50_val:.2f}, MA200: {ma200_val:.2f}")

                if ma50_val > ma200_val:
                    strength = ((ma50_val / ma200_val) - 1) * 100
                    roast = info(ticker,strength,5)
                    
                    bullish_stocks.append({
                        "symbol": ticker,
                        "close": round(latest['Close'], 2),
                        "strength_pct": round(strength, 1),
                        "info": info(ticker,strength,"bullish")
                    })
                    
                    fig = go.Figure()

                    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], 
                                            mode='lines', 
                                            name='Close Price',
                                            line=dict(color='#F5C518', width=2.5)))  # ← yellow gold for price line

                    fig.add_trace(go.Scatter(x=data.index, y=data['MA50'], 
                                            name='50-day MA',
                                            line=dict(color='#FFFFFF', width=1.8, dash='dash')))  # white dashed for contrast

                    fig.add_trace(go.Scatter(x=data.index, y=data['MA200'], 
                                            name='200-day MA',
                                            line=dict(color='#AAAAAA', width=1.5, dash='dot')))  # light gray dot

                   
                    fig.update_layout(
                        template="plotly_dark",
                        width=1350,
                        height=450,
                        title=f"{ticker} - Bullish Vibes",
                        title_font=dict(size=20, color="#F5C518"),  # this one is for the MAIN figure title — still uses title_font (not titlefont)
                        paper_bgcolor="#0F0F0F",
                        plot_bgcolor="#111111",
                        font=dict(color="#E0E0E0"),
                        hovermode="x unified",
                        legend=dict(
                            bgcolor="rgba(0,0,0,0.5)",
                            bordercolor="#F5C518",
                            borderwidth=1,
                            font=dict(color="#F5C518")
                        ),
                        xaxis=dict(
                            title="Date",
                            title_font=dict(color="#F5C518"),   # ← FIXED: title_font (with underscore), nested
                            gridcolor="#333333",
                            zerolinecolor="#444444"
                        ),
                        yaxis=dict(
                            title="Price (₹)",
                            title_font=dict(color="#F5C518"),   # ← FIXED here too
                            gridcolor="#333333",
                            zerolinecolor="#444444"
                        ),
                        margin=dict(l=50, r=30, t=60, b=50)
                    )
                    # Hover still has your roast — make the hover box pop
                    fig.update_traces(
                        hovertemplate="%{y:.2f} ₹<br>%{x|%d %b %Y}<br><b>Roast:</b> " + roast.replace("\n", "<br>"),
                        hoverlabel=dict(
                            bgcolor="#1A1A1A",
                            font_color="#F5C518",
                            bordercolor="#F5C518"
                        )
                    )
                    graphs_html.append(pio.to_html(fig, full_html=False, div_id=f"graph-{ticker}"))
                    
                    print(f"DEBUG: {ticker} added — strength {strength:.1f}%")
                else:
                    print(f"DEBUG: {ticker} not bullish right now")
                    
            except Exception as e:
                print(f"CRASH on {ticker}: {str(e)}")
                import traceback
                traceback.print_exc()

        print(f"DEBUG: Loop done - {len(bullish_stocks)} stocks found")
        bullish_stocks.sort(key=lambda x: x['strength_pct'], reverse=True)
    return render_template("stocks.html",
            bullish_stocks=bullish_stocks,
        graphs=graphs_html
        )

    

    


if __name__  == "__main__":

    app.run(debug=True)



