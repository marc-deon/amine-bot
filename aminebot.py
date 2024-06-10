#!/usr/bin/env python3

# Warning: there IS some strangely written cruft in this file that remains as I didn't know better
# when I wrote those chunks ~4 years ago for another project.

# API Reference: https://myanimelist.net/apiconfig/references/api/v2#section/Authentication

import sys
import requests
import json
import os
import secrets
from datetime import timedelta, timezone
import mal
from SerializableDatetime import SerializableDatetime, now
from math import ceil
import urllib.parse
from Message import Message

JAPAN = timezone(timedelta(hours=9))

TOKEN_NAME = "token.json"
ARCHIVE_NAME = "anime-list.json"
CONFIG_ROOT = os.path.expanduser("~/.config/aminebot")
config = {}
shows = {}


def increment_previous_datetime(show) -> None:
    shows[show]["previous_date"] = now(JAPAN).isoformat()


def check_for_updates() -> list:
    ids = []
    for id, show in shows.items():
        if show["previous_date"] + timedelta(days=6.99) < now(JAPAN):
            ids.append(id)
    return ids


# region Config and Authorization
def ReadConfig():
    global config
    global shows

    global token
    
    config_path = os.path.join(CONFIG_ROOT, "config.json")
    shows_path = os.path.join(CONFIG_ROOT, "shows.json")
    token_path = os.path.join(CONFIG_ROOT, "token.json")
    # Load Config file
    try:
        config = json.load(open(config_path))
    except:
        config = {}
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, 'w') as f:
            f.write("{\n\n}")

    # Load Token file
    try:
        with open(token_path, 'r') as file:
            # return token
            token = json.loads(file.read())
    except:
        code_challenge = get_new_code_verifier()
        print_new_authorisation_url(code_challenge)
        authorisation_code = input("Copy-paste the authorisation code: ").strip()
        token = generate_new_token(authorisation_code, code_challenge)
        token['aquired'] = now()
        save_token()
        #return retrieve_token()

    config["token"] = token

    # Load Shows file
    try:
        shows = json.load(open(shows_path))
    except:
        shows = {}
        os.makedirs(os.path.dirname(shows_path), exist_ok=True)
        with open(shows_path, 'w') as f:
            f.write("{\n\n}")

    if "MAL_CLIENT_ID" not in config:
        exit("Must have MAL_CLIENT_ID in config!")
    if "MAL_CLIENT_SECRET" not in config:
        exit("Must have MAL_CLIENT_SECRET in config!")

    try:
        token = json.load(open(os.path.join(CONFIG_ROOT, TOKEN_NAME)))
    except:
        with open(os.path.join(CONFIG_ROOT, TOKEN_NAME)) as f:
            f.write("{\n\n}")
            exit("Must have DISCORD_TOKEN in token.json!")
        pass

    for show in shows:
        if "previous_date" in shows[show]:
            shows[show]["previous_date"] = SerializableDatetime.fromisoformat(shows[show]["previous_date"])
        else:
            shows[show]["previous_date"] = SerializableDatetime(1970, 1, 1, tzinfo=JAPAN)

        if "skipped" not in shows[show]:
            shows[show]["skipped"] = 0

        if "previous_episode" not in shows[show]:
            shows[show]["previous_episode"] = 0

    return config

def SaveConfig():
    json.dump(config, open(os.path.join(CONFIG_ROOT, "config.json"), 'w'), default=lambda x: x.ToDict(), indent=2)

def SaveShows():
    json.dump(shows, open(os.path.join(CONFIG_ROOT, "shows.json"), 'w'), default=lambda x: x.ToDict(), indent=2)

def get_new_code_verifier():
    token = secrets.token_urlsafe(100)
    return token[:128]


def print_new_authorisation_url(code_challenge:str):
    #global MAL_CLIENT_ID, MAL_CLIENT_SECRET
    MAL_CLIENT_ID = config["MAL_CLIENT_ID"]
    MAL_CLIENT_SECRET = config["MAL_CLIENT_SECRET"]
    print("new auth irl")
    url = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&client_id={MAL_CLIENT_ID}&code_challenge={code_challenge}'
    print(f'Authorise your application by clicking here: {url}\n')


# 3. Once you've authorised your application, you will be redirected to the webpage you've
#    specified in the API panel. The URL will contain a parameter named "code" (the Authorisation
#    Code). You need to feed that code to the application.
def generate_new_token(authorisation_code: str, code_verifier: str) -> dict:
    global MAL_CLIENT_ID, MAL_CLIENT_SECRET
    global token
    print("new token")

    url = 'https://myanimelist.net/v1/oauth2/token'
    data = {
        'client_id': config["MAL_CLIENT_ID"],
        'client_secret': config["MAL_CLIENT_SECRET"],
        'code': authorisation_code,
        'code_verifier': code_verifier,
        'grant_type': 'authorization_code'
    }

    response = requests.post(url, data)
    response.raise_for_status()  # Check whether the requests contains errors

    token = response.json()
    response.close()
    print('Token generated successfully!')

    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'w') as file:
        json.dump(token, file, indent = 4)
        print('Token saved in "token.json"')

    return token


def refresh_token(refresh_token:str) -> dict:
    global token
    print("refresh token:", refresh_token)
    url = "https://myanimelist.net/v1/oauth2/token"

    data = {
            "MAL_client_id": config["MAL_CLIENT_ID"],
            "MAL_client_secret": config["MAL_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
    }
    print(data)

    response = requests.post(url, data=data)
    response.raise_for_status()

    token = response.json()
    response.close()
    print("Token refreshed successfully!")

    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'w') as file:
        json.dump(token, file, indent = 4)
        print('Token saved in "token.json"')

    token["aquired"] = now()
    config["token"] = token
    return token


#def retrieve_token():
    
def save_token():
    temp = token["aquired"]
    token["aquired"] = repr(temp)
    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'w') as file:
        file.write(json.dumps(token))
    token["aquired"] = temp
    pass

#endregion

def ShowCalendar():
    import subprocess
    cal = subprocess.Popen('cal', shell=True, stdout=subprocess.PIPE).stdout.read().decode()
    weeks = cal.split("\n")

            # Su Mo Tu We Th Fr Sa
    counts = [0, 0, 0, 0, 0, 0, 0]

    for id, show in shows.items():
        show["start_date"] = SerializableDatetime.fromisoformat(show["start_date"])
        dow = int(show["start_date"].strftime('%w'))
        counts[dow]+=1

    print(counts)

    white = "\033[0m"
    green = "\033[1;32m"
    blue  = "\033[1;34m"
    purple= "\033[35m"
    orange= "\033[1;33m"
    end = "\033[0m"


    print(weeks[0])
    print(weeks[1])
    for week in weeks[2:]:
        if not week.strip():
            break
        days = [
            week[0:0+2] + end,
            week[3:3+2] + end,
            week[6:6+2] + end,
            week[9:9+2] + end,
            week[12:12+2] + end,
            week[15:15+2] + end,
            week[18:18+2] + end,
        ]
        for dow in range(7):
            n = counts[dow]
            color = orange if n >= 4 else purple if n >= 3 else blue if n >= 2 else green if n >= 1 else white
            print(color, days[dow], " ", sep="", end="")
        print()


def CheckMalToken():
    
    pass


if __name__ == "__main__":


    ReadConfig()
    #token = retrieve_token()
    #config["token"] = token

    if "--test-bot" in sys.argv:
        import discord_side
        token = config["DISCORD_TOKEN"]
        discord_side.test(token)
        exit()


    if "--show_cal" in sys.argv:
        ShowCalendar()
        exit()

    if "aquired" in config["token"]:
        # stored as string "datetime.datetime(y,m,d,h,m)"
        # There's no reason to not store this in isoformat, I just didn't know it
        # was an option when this chunk of code was written ~4 years earlier
        parts = []
        for part in config["token"]["aquired"].split(","):
            part = ''.join(list(filter(lambda c: c.isdigit(), part)))
            parts.append(int(part))

        config["token"]["aquired"] = SerializableDatetime(*parts)
    else:
        config["token"]["aquired"] = SerializableDatetime(1970,1,1)


    if (now() - config["token"]["aquired"]).days >= 15:
        config["token"] = refresh_token(config["token"]["refresh_token"])
        save_token()

    messages = []
    for id, show in shows.items():

        # Get the previous date and nickname
        # Take from MAL if necessary
        if "start_date" not in show or "name" not in show:
            # Get rest of info
            info = mal.get_anime_info(config["token"]["access_token"], id)
            show["title"] = info["title"]

            # convert start date + broadcast time to datetime
            start_date = SerializableDatetime.fromisoformat(info["start_date"])
            hh, mm = info["broadcast"]["start_time"].split(":")
            start_date = start_date.replace(hour=int(hh), minute=int(mm), tzinfo=JAPAN)
            show["start_date"] = start_date

        name = show["nickname"] if "nickname" in show else show["title"]
        start_date = show["start_date"]

        # Get current time
        current_date = now(JAPAN)

        # Find latest episode number
        diff = current_date - start_date
        SECONDS_IN_WEEK = 3600 * 24 * 7 - 120 # Tweak this by just a couple minutes
        floating = diff.total_seconds() / SECONDS_IN_WEEK
        episode_num = ceil(floating) - show["skipped"]

        #print(name, floating, episode_num, start_date, current_date, "\n", sep="\n")

        # Skip unaired shows
        if episode_num < 1:
            continue

        # embed=info['main_picture']['medium']
        m = Message(link=f"https://myanimelist.net/anime/{id}")

        if info["num_episodes"] > 0 and episode_num > info["num_episodes"]:
            # Create a message for ended shows
            m.message = f"{name} has ended after {info['num_episodes']} episodes."
            messages.append(m)

        elif episode_num > show["previous_episode"]:
            # Create message for new episode
            print("New ep!")
            m.message = f"""{name} episode #{episode_num} is out!"""
            m.link += "\n<https://nyaa.si/?f=0&c=0_0&q=" + urllib.parse.quote(info["title"]) + ">"
            #increment_previous_datetime(id)
            show["previous_episode"] = episode_num
            messages.append(m)


    if messages:
        # Save back to file
        SaveShows()
        print("Saving...")
    else:
        exit()

    if "--test" in sys.argv:
        exit()


    import discord_side
    token = config["DISCORD_TOKEN"]
    discord_side.begin(messages, token)
