import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import requests
import time
import json
import os
from collections import defaultdict
import asyncio
import aiohttp
import pandas as pd


# API Key and Region Setup
API_KEY = 'RGAPI-e22ad9f8-5497-4171-8095-1841e490b135'
REGION = 'na1'
AMERICAS_REGION = 'americas'
MATCH_COUNT = 5


# Helper functions (copied from your original scripts)

def get_high_tier_summoner_ids(queue='RANKED_SOLO_5x5'):
    tiers = ['challengerleagues', 'grandmasterleagues', 'masterleagues']
    summoner_ids = set()
    headers = {'X-Riot-Token': API_KEY}

    for tier in tiers:
        url = f'https://{REGION}.api.riotgames.com/lol/league/v4/{tier}/by-queue/{queue}'
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            entries = data.get('entries', [])
            for entry in entries:
                if 'summonerId' in entry:
                    summoner_ids.add(entry['summonerId'])
        time.sleep(1.2)
    return list(summoner_ids)


def load_puuid_cache():
    if os.path.exists('puuid_cache.json'):
        with open('puuid_cache.json', 'r') as f:
            return json.load(f)
    else:
        return {}


def save_puuid_cache(cache):
    with open('puuid_cache.json', 'w') as f:
        json.dump(cache, f)


async def fetch_puuid(session, summoner_id, semaphore):
    async with semaphore:
        url = f'https://{REGION}.api.riotgames.com/lol/summoner/v4/summoners/{summoner_id}'
        headers = {'X-Riot-Token': API_KEY}
        retries = 0
        while retries < 5:
            try:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return summoner_id, data['puuid']
                    elif response.status == 429:
                        retry_after = int(response.headers.get('Retry-After', '1'))
                        await asyncio.sleep(retry_after)
                        retries += 1
                    else:
                        return summoner_id, None
            except:
                return summoner_id, None
        return summoner_id, None


async def get_puuids_from_summoner_ids_async(summoner_ids):
    puuid_dict = {}
    semaphore = asyncio.Semaphore(1)
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_puuid(session, summoner_id, semaphore) for summoner_id in summoner_ids]
        for future in asyncio.as_completed(tasks):
            summoner_id, puuid = await future
            if puuid is not None:
                puuid_dict[summoner_id] = puuid
    return puuid_dict


def get_puuids_from_summoner_ids(summoner_ids):
    cache = load_puuid_cache()
    uncached_summoner_ids = [sid for sid in summoner_ids if sid not in cache]

    if uncached_summoner_ids:
        new_puuid_dict = asyncio.run(get_puuids_from_summoner_ids_async(uncached_summoner_ids))
        cache.update(new_puuid_dict)
        save_puuid_cache(cache)
    
    puuids = [cache[sid] for sid in summoner_ids if sid in cache and cache[sid] is not None]
    return puuids


def get_match_ids_by_puuid(puuid, count=MATCH_COUNT):
    url = f'https://{AMERICAS_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}'
    headers = {'X-Riot-Token': API_KEY}
    retries = 0
    while retries < 5:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            time.sleep(1.2)
            return response.json()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', '1'))
            time.sleep(retry_after)
            retries += 1
        else:
            return []
    return []


def get_match_data(match_id):
    url = f'https://{AMERICAS_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': API_KEY}
    retries = 0
    while retries < 5:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            time.sleep(1.2)
            return response.json()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', '1'))
            time.sleep(retry_after)
            retries += 1
        else:
            return None
    return None


def analyze_counters(champion_name):
    print(f"Analyzing counters for {champion_name}...")

    # Fetching summoner IDs of Master+ players
    summoner_ids = get_high_tier_summoner_ids()
    summoner_ids = summoner_ids[:100]  # Limit for testing

    print("Fetching PUUIDs...")
    puuids = get_puuids_from_summoner_ids(summoner_ids)

    match_ids = set()
    for puuid in puuids:
        matches = get_match_ids_by_puuid(puuid)
        match_ids.update(matches)

    print(f"Total matches: {len(match_ids)}")
    counter_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

    for match_id in match_ids:
        match_data = get_match_data(match_id)
        if not match_data:
            continue

        participants = match_data['info']['participants']
        target_player = next((p for p in participants if p['championName'].lower() == champion_name.lower()), None)
        if not target_player:
            continue
        
        team_id = target_player['teamId']
        win = target_player['win']

        for opponent in participants:
            if opponent['teamId'] != team_id:
                opponent_name = opponent['championName']
                counter_stats[opponent_name]['games'] += 1
                if not win:
                    counter_stats[opponent_name]['wins'] += 1

    # Sorting opponents by win rate
    for opponent in counter_stats:
        stats = counter_stats[opponent]
        stats['win_rate'] = (stats['wins'] / stats['games']) * 100 if stats['games'] > 0 else 0

    top_counters = sorted(counter_stats.items(), key=lambda x: x[1]['win_rate'], reverse=True)[:5]

    # Output the results
    output = f"Top 5 counters against {champion_name}:\n"
    for idx, (opponent, stats) in enumerate(top_counters, 1):
        output += f"{idx}. {opponent} - Win Rate: {stats['win_rate']:.2f}% over {stats['games']} games\n"

    return output


def get_top_counters(champion_name):
    print(f"Loading datasets for {champion_name}...")

    try:
        participants = pd.read_csv('participants.csv')
        champs = pd.read_csv('champs.csv')
        matches = pd.read_csv('matches.csv')

        participants = participants.merge(champs, left_on='championid', right_on='id', how='left')
        participants.rename(columns={'name': 'champion_name'}, inplace=True)
        champion_name = champion_name.capitalize()

        if champion_name not in participants['champion_name'].unique():
            return f"Champion '{champion_name}' not found in the dataset."

        target_champion_data = participants[participants['champion_name'] == champion_name]
        match_ids = target_champion_data['matchid'].unique()
        matches_data = participants[participants['matchid'].isin(match_ids)]

        counter_stats = {}

        for match_id in match_ids:
            match_participants = matches_data[matches_data['matchid'] == match_id]
            target_player = match_participants[match_participants['champion_name'] == champion_name].iloc[0]
            target_team = 'blue' if target_player['player'] <= 5 else 'red'

            opponent_team_players = match_participants[match_participants['player'] > 5] if target_team == 'blue' else \
                match_participants[match_participants['player'] <= 5]

            for _, opponent in opponent_team_players.iterrows():
                opponent_name = opponent['champion_name']
                if pd.isnull(opponent_name):
                    continue
                if opponent_name not in counter_stats:
                    counter_stats[opponent_name] = {'games': 0}
                counter_stats[opponent_name]['games'] += 1

        counters = sorted(counter_stats.items(), key=lambda x: x[1]['games'], reverse=True)
        top_5_counters = counters[:5]

        output = f"Top 5 counters against {champion_name} from dataset:\n"
        for idx, (opponent, stats) in enumerate(top_5_counters, 1):
            output += f"{idx}. {opponent} - Games Played: {stats['games']}\n"

        return output
    except Exception as e:
        return f"Error loading datasets: {e}"


# GUI Implementation

def create_gui():
    def on_analyze_button_click():
        champion_name = champion_entry.get()
        if not champion_name:
            messagebox.showerror("Error", "Please enter a champion name.")
            return
        result = analyze_counters(champion_name)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, result)

    def on_get_top_counters_button_click():
        champion_name = champion_entry.get()
        if not champion_name:
            messagebox.showerror("Error", "Please enter a champion name.")
            return
        result = get_top_counters(champion_name)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, result)

    window = tk.Tk()
    window.title("Champion Counter Analyzer")

    # Champion Name Entry
    champion_label = tk.Label(window, text="Champion Name:")
    champion_label.grid(row=0, column=0)
    champion_entry = tk.Entry(window)
    champion_entry.grid(row=0, column=1)

    # Buttons
    analyze_button = tk.Button(window, text="Analyze Counters", command=on_analyze_button_click)
    analyze_button.grid(row=1, column=0, padx=10, pady=10)

    top_counters_button = tk.Button(window, text="Get Top Counters", command=on_get_top_counters_button_click)
    top_counters_button.grid(row=1, column=1, padx=10, pady=10)

    # Result Display
    result_text = scrolledtext.ScrolledText(window, width=50, height=15)
    result_text.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    window.mainloop()


create_gui()
