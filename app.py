import os
from flask import Flask, render_template, request
import requests
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
STEAM_API_KEY = os.environ.get('STEAM_API_KEY')

@app.route('/', methods=['GET', 'POST'])
def index():
    player_data = None
    games_data = None
    error_message = None

    if request.method == 'POST':
        # 1. Get user input and clean off accidental spaces
        user_input = request.form.get('steamid').strip()

        # --- NEW: URL PARSING LOGIC ---
        # If they pasted a full Steam link, extract the ID/Name at the end
        if "steamcommunity.com" in user_input:
            # Remove any trailing slashes, then split the URL by '/'
            url_parts = user_input.rstrip('/').split('/')
            # Grab the very last element as the user input (could be a vanity name or SteamID64)
            user_input = url_parts[-1]
        # ------------------------------

        steam_id = user_input

        try:
            # 2. Check if the input is a vanity URL (not 17 digits)
            if not (user_input.isdigit() and len(user_input) == 17):
                vanity_url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={STEAM_API_KEY}&vanityurl={user_input}"
                vanity_res = requests.get(vanity_url).json()
                
                if vanity_res.get('response', {}).get('success') == 1:
                    steam_id = vanity_res['response']['steamid']
                else:
                    error_message = "Could not find a user with that custom URL or ID."
                    return render_template('index.html', error=error_message)

            # 3. Fetch Data with the finalized SteamID64
            summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={STEAM_API_KEY}&steamids={steam_id}"
            games_url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={STEAM_API_KEY}&steamid={steam_id}&include_appinfo=1&format=json"

            # Profile Summary
            summary_res = requests.get(summary_url).json()
            players = summary_res.get('response', {}).get('players', [])
            
            if players:
                player_data = players[0]
                
                # Games Data
                games_res = requests.get(games_url).json()
                response_data = games_res.get('response', {})
                
                if 'games' in response_data:
                    games_list = response_data['games']
                    games_list.sort(key=lambda x: x.get('playtime_forever', 0), reverse=True)
                    games_data = {
                        'total_games': response_data.get('game_count', 0),
                        'top_games': games_list[:5]
                    }
                else:
                    games_data = {'private': True}
            else:
                error_message = "Profile found, but no data could be retrieved."

        except Exception as e:
            error_message = "Error communicating with Steam API."
            print(f"Error: {e}") 

    return render_template('index.html', player=player_data, games=games_data, error=error_message)

if __name__ == '__main__':
    app.run(debug=True)