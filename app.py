from flask import Flask, render_template, request, redirect, url_for, session
import requests
import secrets
from key import apikey

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

REGION_MAP = {
    'americas': ['br1', 'la1', 'la2', 'na1'],
    'asia': ['jp1', 'kr', 'oc1', 'ph2', 'sg2', 'th2', 'tw2', 'vn2'],
    'europe': ['eun1', 'euw1', 'tr1', 'ru']
}

def get_region(platform):
    for region, platforms in REGION_MAP.items():
        if platform in platforms:
            return region
    return None

def get_version():
    url = "https://ddragon.leagueoflegends.com/api/versions.json"
    response = requests.get(url)
    ver = response.json()
    return ver[0]

def get_champ_list(ver):
    url = f"https://ddragon.leagueoflegends.com/cdn/{ver}/data/en_US/champion.json"
    response = requests.get(url)
    champion_data = response.json()
    champions = champion_data['data']
    champion_list = sorted([(champion['key'], champion['id'], champion['name']) for champion in champions.values()], key=lambda x: x[2])
    return champion_list

def get_puuid(summoner_name, tagline, platform):
    region = get_region(platform)
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}?api_key={apikey.RIOT_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('puuid'), region
    return None, None

def get_champion_mastery(puuid, platform, champion_key):
    url = f"https://{platform}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-puuid/{puuid}/by-champion/{champion_key}?api_key={apikey.RIOT_API_KEY}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get('championLevel')
    return None

def get_champion_details(champion_id, version):
    url = f"https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{champion_id}.json"
    response = requests.get(url)
    if response.status_code != 200:
        return None
    data = response.json()['data'][champion_id]
    return {
        'tags': data.get('tags', []),
        'stats': data.get('stats', {}),
        'abilities': {
            'Passive': data['passive']['name'],
            'Q': data['spells'][0]['name'],
            'W': data['spells'][1]['name'],
            'E': data['spells'][2]['name'],
            'R': data['spells'][3]['name'],
        },
        'resource_type': data.get('partype', '')
    }

@app.route('/')
def top():
    return render_template('top.html')

@app.route('/set_user', methods=['POST'])
def set_user():
    summoner_name = request.form['summoner_name']
    tagline = request.form['tagline']
    platform = request.form['platform']
    puuid, region = get_puuid(summoner_name, tagline, platform)
    if puuid:
        session['puuid'] = puuid
        session['region'] = region
        session['platform'] = platform
        return redirect(url_for('index'))
    else:
        return render_template('id_error.html', message="PUUIDを取得できませんでした。入力情報を確認してください。")

@app.route('/index')
def index():
    version = get_version()
    champions = get_champ_list(version)
    return render_template('index.html', champions=champions)

@app.route('/champion/<champion_id>/<champion_key>')
def champion(champion_id, champion_key):
    version = get_version()
    details = get_champion_details(champion_id, version)
    if details is None:
        return render_template('champ_error.html', message="チャンピオンの詳細を取得できませんでした。")
    
    puuid = session.get('puuid')
    platform = session.get('platform')
    mastery_level = get_champion_mastery(puuid, platform, champion_key)
    
    return render_template('champion.html', champion_id=champion_id, champion_key=champion_key, mastery_level=mastery_level, details=details)

@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form.get('query')
        version = get_version()
        champions = get_champ_list(version)
        search_results = [champion for champion in champions if query.lower() in champion[2].lower()]
        return render_template('search_results.html', query=query, search_results=search_results)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
