import pandas as pd
import json
import requests
from bs4 import BeautifulSoup


# Returns list of lists with [[Team 1 vs. Team 2, Start time], [Team 1 vs. Team 2, Start time]]
def get_oddsshark_matchups(soup_content):
    # Matchup times
    game_times = []
    times = soup_content.find_all('div', {'class': 'op-matchup-time op-matchup-text'})
    for time in times:
        game_times.append(time.get_text())

    # Team 1
    top_teams = []
    team1 = soup_content.find_all('div', {'class': 'op-matchup-team op-matchup-text op-team-top'})
    for team in team1:
        top_teams.append(team.get_text())

    # Team 2
    bottom_teams = []
    team2 = soup_content.find_all('div', {'class': 'op-matchup-team op-matchup-text op-team-bottom'})
    for team in team2:
        bottom_teams.append(team.get_text())

    # Combining into list of lists
    matchup_info = []
    for x in range(0, len(game_times)):
        temp = [top_teams[x] + ' vs. ' + bottom_teams[x], game_times[x]]
        matchup_info.append(temp)

    return matchup_info


# Returns the odds from each sportsbook in list of lists [[Column 1 from site], [Column 2 from site], ... , [] ]
def get_oddsshark_odds(soup_content):
    books = ['op-item op-spread op-opening', 'op-item op-spread op-bovada.lv', 'op-item op-spread op-betonline',
             'op-item op-spread op-intertops', 'op-item op-spread op-sportsbetting', 'op-item op-spread op-betnow',
             'op-item op-spread op-gtbets', 'op-item op-spread op-skybook', 'op-item op-spread op-5dimes',
             'op-item op-spread op-sportbet']

    oddlist = []
    for sportsbook in books:
        odds = soup_content.find_all('div', {'class': sportsbook})
        temp = []

        for odd in odds:
            number = json.loads(odd["data-op-moneyline"])
            temp.append(number['fullgame'])
        oddlist.append(temp)

    return oddlist


# Returns list of lists of the scraped odds that formats in manner that fits dictionary columns
def format_odds_list(odds):
    formatted = []
    for x in range(0, len(odds)):
        temp1 = []
        temp2 = []
        for y in range(0, len(odds[x])):
            if y % 2 == 0:
                temp1.append(odds[x][y])
            else:
                temp2.append(odds[x][y])
        formatted.append(temp1)
        formatted.append(temp2)

    return formatted


# Returns dictionary of the match, start time, and the odds from each book for each team.
def game_dictionary(matchup_list, odds):
    game_dict = {}
    game_dict["Match"] = [matchup[0] for matchup in matchup_list]
    game_dict["Start Time"] = [matchup[1] for matchup in matchup_list]
    column_names = ["Opening Odds Team 1", "Opening Odds Team 2", "Bovada Odds Team 1", "Bovada Odds Team 2",
                    "BetOnline Odds Team 1", "BetOnline Odds Team 2", "Intertops Odds Team 1", "Intertops Odds Team 2",
                    "Sportsbetting Odds Team 1", "Sportsbetting Odds Team 2", "BetNow Odds Team 1",
                    "BetNow Odds Team 2", "GTBets Odds Team 1", "GTBets Odds Team 2", "Skybook Odds Team 1",
                    "Skybook Odds Team 2", "5Dimes Odds Team 1", "5Dimes Odds Team 2", "SportBet Odds Team 1",
                    "SportBet Odds Team 2"]
    counter = 0
    for col in column_names:
        game_dict[col] = odds[counter]
        counter = counter + 1

    return game_dict


# Returns a list of lists with the odds turned into MM's.
def mm_list(formatted_list):
    res = []
    for sb in formatted_list:
        temp = []
        for x in range(0, len(sb)):

            if sb[x] == "":
                temp.append(0)
            elif sb[x][0] == "+":
                val = int(sb[x][1:])
                temp.append((val + 100) / 100)
            elif sb[x][0] == "-":
                val = int(sb[x][1:])
                temp.append((val + 100) / val)
        res.append(temp)

    return res


# Function to return the different combinations of sportsbooks to check arbitrage opportunities for.
# Take in the mmdf and return a dataframe with columns made to represent every combo and the MMs formula done.
def arbitrage_opportunities(df, teams):
    cols = list(df.columns[2:])
    t1s = []
    t2s = []
    combos = []
    t1key = []
    t2key = []

    for x in range(0, len(cols), 2):
        t1s.append(cols[x])
        t2s.append(cols[x + 1])

    for x in range(0, len(t1s)):
        for y in range(0, len(t2s)):
            t1key.append(t1s[x])
            t2key.append(t2s[y])
            combos.append(str(t1s[x]) + ", " + str(t2s[y]))

    adf = pd.DataFrame(index=teams, columns=combos)

    for x in range(0, len(combos)):
        adf[combos[x]] = arbitrage_opportunity_solver(df[t1key[x]].values, df[t2key[x]].values)

    return adf


# Takes in two series, runs calculations on the two mm's (one from each team), and then returns a single series of True
# or False values depending on if conditions are met. Return true if the mm1, mm2 combo is conducive to an arbitrage
def arbitrage_opportunity_solver(mm1_series, mm2_series):
    # slope = float(-1 * (mm1_series - 2) / (mm2_series - 2))
    res1 = []
    res2 = []
    final = []

    # conditions for mm1
    for row in mm1_series:
        if row > 2:
            res1.append(True)
        else:
            res1.append(False)

    # conditions for mm2
    for row in mm2_series:
        if row > 2:
            res2.append(True)
        else:
            res2.append(False)

    # conditions for both of them
    for x in range(0, len(res1)):
        if (res1[x] == True) & (res2[x] == True):
            final.append(True)
        else:
            final.append(False)

    return final


def runner():
    sports = ['nfl', 'ncaaf', 'nba', 'ncaab', 'mlb', 'nhl', 'ufc']
    writer = pd.ExcelWriter('sports_betting_arbitrage.xlsx', engine='xlsxwriter')

    for sport in sports:
        # get data from the site for each sport since they are each on different urls.
        url = 'https://www.oddsshark.com/' + sport + '/odds'
        oddsshark = requests.get(url)
        soup = BeautifulSoup(oddsshark.content, 'html.parser')

        # create variables for items to use in dataframe construction, this way we prevent unnecessary calculations.
        matches = get_oddsshark_matchups(soup)
        teams = [game[0] for game in matches]
        all_odds = format_odds_list(get_oddsshark_odds(soup))
        decimal_odds = mm_list(all_odds)

        # create dataframes for the odds, decimal odds, and the arbitrage opportunities.
        odds_df = pd.DataFrame.from_dict(game_dictionary(matches, all_odds))
        decimal_df = pd.DataFrame.from_dict(game_dictionary(matches, decimal_odds))
        arb_df = arbitrage_opportunities(decimal_df, teams)

        # output the dataframes to excel, using a different sheet for each sport.
        odds_df.to_excel(writer, sheet_name=str(sport))
        decimal_df.to_excel(writer, sheet_name=str(sport), startrow=len(odds_df) + 4)
        arb_df.to_excel(writer, sheet_name=str(sport), startrow=(2 * (len(odds_df) + 4)))
    writer.save()


# Returns a dataframe out of the dictionary with all the info.
def dict_to_df(game_dict):
    return pd.DataFrame.from_dict(game_dict)


# Function to output the dataframe to an excel file.
def to_xlsx(df):
    df.to_excel("odds.xlsx")