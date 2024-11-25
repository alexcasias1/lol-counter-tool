import requests
from collections import defaultdict
import time
import asyncio
import aiohttp
import os
import json

# Replace 'YOUR_API_KEY' with your Riot Games API key
API_KEY = 'RGAPI-e22ad9f8-5497-4171-8095-1841e490b135'
REGION = 'na1'  # Replace with the region appropriate for your analysis
AMERICAS_REGION = 'americas'  # For match data; adjust if necessary
MATCH_COUNT = 5  # Number of recent matches per player to analyze

def get_high_tier_summoner_ids(queue='RANKED_SOLO_5x5'):
    """
    Fetch summoner IDs of all players in Challenger, Grandmaster, and Master tiers.
    """
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
                else:
                    print(f"Key 'summonerId' not found in entry: {entry}")
        else:
            print(f"Error fetching {tier} data: {response.status_code} - {response.text}")
        time.sleep(1.2)  # Rate limiting

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
                        print(f"Rate limit hit. Retrying after {retry_after} seconds.")
                        await asyncio.sleep(retry_after)
                        retries += 1
                    else:
                        print(f"Error fetching PUUID for Summoner ID {summoner_id}: {response.status}")
                        return summoner_id, None
            except Exception as e:
                print(f"Exception fetching PUUID for Summoner ID {summoner_id}: {e}")
                return summoner_id, None
        print(f"Failed to fetch PUUID for Summoner ID {summoner_id} after retries.")
        return summoner_id, None

async def get_puuids_from_summoner_ids_async(summoner_ids):
    puuid_dict = {}
    semaphore = asyncio.Semaphore(1)  # Limit concurrent requests to 1
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
        print(f"Fetching PUUIDs for {len(uncached_summoner_ids)} new summoner IDs...")
        new_puuid_dict = asyncio.run(get_puuids_from_summoner_ids_async(uncached_summoner_ids))
        cache.update(new_puuid_dict)
        save_puuid_cache(cache)
    else:
        print("All PUUIDs are cached.")

    puuids = [cache[sid] for sid in summoner_ids if sid in cache and cache[sid] is not None]
    return puuids

def get_match_ids_by_puuid(puuid, count=MATCH_COUNT):
    url = f'https://{AMERICAS_REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={count}'
    headers = {'X-Riot-Token': API_KEY}
    retries = 0
    while retries < 5:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            time.sleep(1.2)  # Rate limiting
            return response.json()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', '1'))
            print(f"Rate limit hit when fetching matches for PUUID {puuid}. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            retries += 1
        else:
            print(f"Error fetching matches for PUUID {puuid}: {response.status_code}")
            return []
    print(f"Failed to fetch matches for PUUID {puuid} after retries.")
    return []

def get_match_data(match_id):
    url = f'https://{AMERICAS_REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}'
    headers = {'X-Riot-Token': API_KEY}
    retries = 0
    while retries < 5:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            time.sleep(1.2)  # Rate limiting
            return response.json()
        elif response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', '1'))
            print(f"Rate limit hit when fetching match {match_id}. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
            retries += 1
        else:
            print(f"Error fetching match {match_id}: {response.status_code}")
            return None
    print(f"Failed to fetch match {match_id} after retries.")
    return None

def filter_matches_by_champion(match_ids, champion_name):
    champion_matches = []
    for idx, match_id in enumerate(match_ids, 1):
        try:
            match_data = get_match_data(match_id)
            if match_data is None:
                continue
            participants = match_data['info']['participants']
            for participant in participants:
                if participant['championName'].lower() == champion_name.lower():
                    champion_matches.append(match_id)
                    break
        except Exception as e:
            print(f"Error fetching match {match_id}: {e}")
        if idx % 100 == 0:
            print(f"Processed {idx} matches for filtering...")
    return champion_matches

def analyze_counters(champion_name):
    """
    Analyze counter statistics for the specified champion.
    """
    print(f"Fetching summoner IDs of Master+ players in {REGION} region...")
    summoner_ids = get_high_tier_summoner_ids()
    print(f"Total Master+ summoners found: {len(summoner_ids)}")

    # Limit summoner IDs to the first 100 for testing
    summoner_ids = summoner_ids[:100]  # Process only the first 100 summoner IDs

    print("Fetching PUUIDs from summoner IDs...")
    puuids = get_puuids_from_summoner_ids(summoner_ids)
    print(f"Total PUUIDs retrieved: {len(puuids)}")

    match_ids = set()
    for idx, puuid in enumerate(puuids, 1):
        try:
            matches = get_match_ids_by_puuid(puuid, count=MATCH_COUNT)
            match_ids.update(matches)
        except Exception as e:
            print(f"Error fetching matches for PUUID {puuid}: {e}")
        time.sleep(1.2)  # Rate limiting
        if idx % 50 == 0:
            print(f"Fetched matches for {idx} PUUIDs...")

    print(f"Total unique matches collected: {len(match_ids)}")

    print(f"Filtering matches for {champion_name.capitalize()}...")
    champion_match_ids = filter_matches_by_champion(match_ids, champion_name)
    print(f"Total matches where {champion_name.capitalize()} was played: {len(champion_match_ids)}")

    counter_stats = defaultdict(lambda: {'wins': 0, 'games': 0})

    print(f"Analyzing {len(champion_match_ids)} matches...")
    for idx, match_id in enumerate(champion_match_ids, 1):
        try:
            match_data = get_match_data(match_id)
            if match_data is None:
                continue
            participants = match_data['info']['participants']

            # Find the target champion's team and win status
            team_id = None
            win = None
            for participant in participants:
                if participant['championName'].lower() == champion_name.lower():
                    team_id = participant['teamId']
                    win = participant['win']
                    break
            if team_id is None:
                continue  # Skip if the champion wasn't found in this match

            # Collect data on opposing champions
            for participant in participants:
                if participant['teamId'] != team_id:
                    opponent_name = participant['championName']
                    counter_stats[opponent_name]['games'] += 1
                    if not win:  # Target champion's loss = opponent's win
                        counter_stats[opponent_name]['wins'] += 1

        except Exception as e:
            print(f"Error processing match {match_id}: {e}")
        if idx % 50 == 0:
            print(f"Processed {idx} matches...")

    # Calculate win rates for each opposing champion
    for opponent in counter_stats:
        stats = counter_stats[opponent]
        stats['win_rate'] = (stats['wins'] / stats['games']) * 100 if stats['games'] > 0 else 0

    # Sort opponents by win rate against the target champion
    top_counters = sorted(counter_stats.items(), key=lambda x: x[1]['win_rate'], reverse=True)[:5]

    print(f"\nTop 5 counters against {champion_name.capitalize()}:")
    for idx, (opponent, stats) in enumerate(top_counters, 1):
        print(f"{idx}. {opponent} - Opponent Win Rate: {stats['win_rate']:.2f}% over {stats['games']} games")

if __name__ == "__main__":
    champion_name = input("Enter the champion name: ")
    try:
        analyze_counters(champion_name)
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except Exception as e:
        print(f"An error occurred: {e}")
