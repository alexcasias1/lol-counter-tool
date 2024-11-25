import pandas as pd

def get_top_counters(champion_name):
    # Load the datasets
    print("Loading datasets... This may take a few minutes.")
    participants = pd.read_csv('participants.csv')
    champs = pd.read_csv('champs.csv')
    matches = pd.read_csv('matches.csv')

    # Merge participants with champs to get champion names
    participants = participants.merge(champs, left_on='championid', right_on='id',how='left')
    participants.rename(columns={'name': 'champion_name'}, inplace=True)

    # Capitalize the champion h name for consistency
    champion_name = champion_name.capitalize()

    # Check if the champion exists in the data
    if champion_name not in participants['champion_name'].unique():
        print(f"Champion '{champion_name}' not found in the dataset.")
        return

    # Get all matches where the champion was played
    target_champion_data = participants[participants['champion_name'] == champion_name]

    if target_champion_data.empty:
        print(f"No matches found for champion '{champion_name}'.")
        return

    # Get unique match IDs
    match_ids = target_champion_data['matchid'].unique()

    # Filter data for these matches
    matches_data = participants[participants['matchid'].isin(match_ids)]

    # Initialize counter stats
    counter_stats = {}

    # Iterate over each match
    for match_id in match_ids:
        match_participants = matches_data[matches_data['matchid'] == match_id]
        target_player = match_participants[match_participants['champion_name'] == champion_name].iloc[0]
        target_team = 'blue' if target_player['player'] <= 5 else 'red'

        # Get opponent team
        if target_team == 'blue':
            opponent_team_players = match_participants[match_participants['player'] > 5]
        else:
            opponent_team_players = match_participants[match_participants['player'] <= 5]

        for idx, opponent in opponent_team_players.iterrows():
            opponent_name = opponent['champion_name']
            if pd.isnull(opponent_name):
                continue

            if opponent_name not in counter_stats:
                counter_stats[opponent_name] = {'games': 0}

            counter_stats[opponent_name]['games'] += 1

    if not counter_stats:
        print(f"No counter data found for champion '{champion_name}'.")
        return

    # Sort opponents by most frequent appearances
    counters = sorted(counter_stats.items(), key=lambda x: x[1]['games'], reverse=True)

    # Get the top 5 counters
    top_5_counters = counters[:5]

    # Display the results
    print(f"\nTop 5 counters against {champion_name}:")
    for idx, (opponent, stats) in enumerate(top_5_counters, 1):
        print(f"{idx}. {opponent} - Games Played: {stats['games']}")

if __name__ == "__main__":
    champion_name = input("Enter the champion name: ")
    get_top_counters(champion_name)