# plot_elo.py

import pandas as pd
import matplotlib.pyplot as plt

print("Wczytywanie features.csv...")
# Wczytujemy dane i od razu konwertujemy datę
df = pd.read_csv("features.csv", parse_dates=["game_date"])

def get_team_elo_history(df, team_name):
    """
    Zbiera historię Elo dla danej drużyny, niezależnie od tego czy grała u siebie, czy na wyjeździe.
    """
    # Wyciągamy mecze u siebie
    home_games = df[df["home_team"] == team_name][["game_date", "home_elo"]].copy()
    home_games.rename(columns={"home_elo": "elo"}, inplace=True)
    
    # Wyciągamy mecze na wyjeździe
    away_games = df[df["away_team"] == team_name][["game_date", "away_elo"]].copy()
    away_games.rename(columns={"away_elo": "elo"}, inplace=True)
    
    # Łączymy i sortujemy chronologicznie po dacie
    team_history = pd.concat([home_games, away_games]).sort_values("game_date")
    return team_history

# ==========================================
# TUTAJ WPISZ SKRÓTY DRUŻYN, KTÓRE CHCESZ ZOBACZYĆ
# (Zmień na takie, jakie masz w swojej bazie, np. "BOS", "LAL" dla NBA)
# ==========================================
TEAMS_TO_PLOT = ["BOS", "LAL", "GSW", "DET","OKC","HUE","SAS","IND","MIL"] 

# Ustawienia wykresu
plt.figure(figsize=(12, 6))

for team in TEAMS_TO_PLOT:
    history = get_team_elo_history(df, team)
    
    # Sprawdzamy czy drużyna w ogóle istnieje w danych
    if history.empty:
        print(f"⚠️ Nie znaleziono drużyny: {team}")
        continue
        
    # Rysujemy linię dla drużyny
    plt.plot(history["game_date"], history["elo"], label=team, linewidth=2)

# Estetyka i opisy
plt.title("Historia rankingu Elo wybranych drużyn", fontsize=14, pad=15)
plt.xlabel("Data meczu", fontsize=12)
plt.ylabel("Rating Elo", fontsize=12)

# Dodajemy poziomą linię bazową (średnia 1500)
plt.axhline(1500, color='black', linestyle='--', alpha=0.5, label='Średnia (1500)')

# Legenda, siatka i formatowanie
plt.legend(loc='best')
plt.grid(True, linestyle=':', alpha=0.7)
plt.tight_layout()

# Wyświetlamy wykres
print("Generowanie wykresu...")
plt.show()