from flask import Flask, render_template, request, session
import datetime as dt
import requests
import os
def kelvin_to_celsius(kelvin):
    return kelvin - 273.15

expression = ""
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/projects", methods=["GET", "POST"])
def projects():
    contents = None
    display = session.get("expression", "0")
    form_type = request.form.get("form_type")

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

    # ---------- FINAL RENDER (ALWAYS) ----------
    return render_template(
        "project.html",
        content=contents,
        display=display
    )

    

    


if __name__  == "__main__":

    app.run(debug=True)
