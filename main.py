import asyncio
import aiohttp
import pysmartthings
import sqlite3
import requests
from datetime import datetime
import xmltodict
import dotenv
import os

dotenv.load_dotenv()

smartthings_api_key = os.getenv('smartthings_api_key')

# SQLite 데이터베이스 초기화
def init_database():
    conn = sqlite3.connect('weather_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            home_temperature REAL,
            home_humidity REAL,
            outdoor_temperature REAL,
            outdoor_humidity REAL
        )
    ''')
    conn.commit()
    conn.close()

# 데이터베이스에 데이터 저장
def save_to_database(timestamp, home_temp, home_hum, outdoor_temp, outdoor_hum):
    conn = sqlite3.connect('weather_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO weather_records (timestamp, home_temperature, home_humidity, outdoor_temperature, outdoor_humidity)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, home_temp, home_hum, outdoor_temp, outdoor_hum))
    conn.commit()
    conn.close()

def get_current_date_string():
    current_date = datetime.now().date()
    return current_date.strftime("%Y%m%d")

def get_current_hour_string():
    now = datetime.now()
    if now.minute < 45:
        if now.hour == 0:
            base_time = "2330"
        else:
            pre_hour = now.hour - 1
            if pre_hour < 10:
                base_time = "0" + str(pre_hour) + "30"
            else:
                base_time = str(pre_hour) + "30"
    else:
        if now.hour < 10:
            base_time = "0" + str(now.hour) + "30"
        else:
            base_time = str(now.hour) + "30"
    return base_time

def forecast():
    datagokr_api_key = os.getenv('datagokr_api_key')
    url = 'http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst'
    params = {
        'serviceKey': datagokr_api_key,
        'pageNo': '1',
        'numOfRows': '1000',
        'dataType': 'XML',
        'base_date': get_current_date_string(),
        'base_time': get_current_hour_string(),
        'nx': '100',
        'ny': '84'
    }

    res = requests.get(url, params=params)
    xml_data = res.text
    dict_data = xmltodict.parse(xml_data)

    weather_data = {}
    for item in dict_data['response']['body']['items']['item']:
        if item['category'] == 'T1H':
            weather_data['tmp'] = item['obsrValue']
        if item['category'] == 'REH':
            weather_data['hum'] = item['obsrValue']
    return weather_data

async def main():
    global home_temp, home_hum
    async with aiohttp.ClientSession() as session:
        api = pysmartthings.SmartThings(session, smartthings_api_key)
        devices = await api.devices()
        device = devices[0]
        await device.status.refresh()
        home_temp = device.status.temperature
        home_hum = device.status.humidity
        print(f'내 집 - 온도: {home_temp}°C, 습도: {home_hum}%')

if __name__ == "__main__":
    # 데이터베이스 초기화
    init_database()

    # 전역 변수 초기화
    home_temp = None
    home_hum = None

    # 현재 시간 저장
    current_time = datetime.now()

    # 집 온도/습도 데이터 수집
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # 실외 날씨 데이터 수집
    outdoor_weather = forecast()
    outdoor_temp = float(outdoor_weather.get('tmp', 0)) if outdoor_weather.get('tmp') else None
    outdoor_hum = float(outdoor_weather.get('hum', 0)) if outdoor_weather.get('hum') else None

    # 데이터베이스에 저장
    save_to_database(current_time, home_temp, home_hum, outdoor_temp, outdoor_hum)

    print(f'범서 현재 날씨 - 온도: {outdoor_temp}°C, 습도: {outdoor_hum}%')
    print(f'데이터가 SQLite 데이터베이스에 저장되었습니다: {current_time}')
