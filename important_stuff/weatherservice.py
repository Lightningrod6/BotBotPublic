import requests
from important_stuff.geolocationapi import get_city
import dotenv
import os
import discord.embeds

dotenv.load_dotenv()

points_api = ""

def get_forecast(city, state = None, zipcode = None):
    try:
        lat_lon = get_city(city, state, zipcode)
        points_api = requests.get(f'https://api.weather.gov/points/{lat_lon}')
        points = points_api.json()
        forecast_api = requests.get(points['properties']['forecast'])
        forecast = forecast_api.json()
    except Exception as e:
        return e
    
    forecasts = []
    getting_station = requests.get(points['properties']['observationStations']).json()
    embed_var = discord.Embed(title="Weather Forecast", description=f"Here is the weather forecast for {city}, {state if state else ' '}")
    for forecasta in forecast['properties']['periods']:
        forecasts.append(f"{forecasta['name']}: {forecasta['detailedForecast']}")
        embed_var.add_field(name=forecasta['name'], value=forecasta['detailedForecast'], inline=False)
    return embed_var
def get_current_forecast(city, state = None, zipcode = None):
    lat_lon = get_city(city, state, zipcode)
    weather_api = requests.get(f"https://api.weatherbit.io/v2.0/current?lat={lat_lon.split(',')[0]}&lon={lat_lon.split(',')[1]}&units=I&key={os.getenv('WEATHER_BIT_API')}")
    weather = weather_api.json()
    temperature = round(weather['data'][0]['temp'])
    feels_like = round(weather['data'][0]['app_temp'])
    wind_speed = round(weather['data'][0]['wind_spd'])
    gust = weather['data'][0]['gust']
    wind_gusts = round(gust) if gust is not None else 0
    wind_direction = weather['data'][0]['wind_cdir']
    dew_point = round(weather['data'][0]['dewpt'])
    humidity = round(weather['data'][0]['rh'])
    visibility = round(weather['data'][0]['vis'])
    state_code = weather['data'][0]['state_code']
    weather_description = weather['data'][0]['weather']['description']
    embed_var = discord.Embed(title="Current Weather", description=f"Here is the current weather for {city}, {state if state else state_code}")
    embed_var.add_field(name="Temperature", value=f"{temperature}°F", inline=True)
    embed_var.add_field(name="Feels Like", value=f"{feels_like}°F", inline=True)
    embed_var.add_field(name="Wind Speed", value=f"{wind_speed} mph", inline=True)
    embed_var.add_field(name="Wind Gusts", value=f"{wind_gusts} mph", inline=True)
    embed_var.add_field(name="Wind Direction", value=wind_direction, inline=True)
    embed_var.add_field(name="Dew Point", value=f"{dew_point}°F", inline=True)
    embed_var.add_field(name="Humidity", value=f"{humidity}%", inline=True)
    embed_var.add_field(name="Visibility", value=f"{visibility} miles", inline=True)
    embed_var.add_field(name="Weather Description", value=weather_description, inline=True)
    return embed_var
def get_alerts(city, state=None, zipcode=None, alerts_per_page=1):
    lat_lon = get_city(city, state, zipcode)
    alerts_api = requests.get(f"https://api.weather.gov/alerts/active?point={lat_lon}")
    alerts = alerts_api.json()['features']
    
    # Create multiple embeds if necessary
    embeds = []
    for i in range(0, len(alerts), alerts_per_page):
        embed = discord.Embed(title="Weather Alerts", description=f"Here are the current weather alerts for {city}, {state}")
        for alert in alerts[i:i+alerts_per_page]:
            if alert is None:
                continue
            embed.add_field(name=alert['properties']['event'], value=alert['properties']['description'], inline=False)
            embed.set_author(name=f"Sent by {alert['properties']['senderName']}")
        embeds.append(embed)
    return embeds if embeds else [discord.Embed(description="No active weather alerts.")]