#!/usr/bin/env python3

# Version 2024-04-09
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

JAPAN = timezone(timedelta(hours=9))

TOKEN_NAME = "token.json"
ARCHIVE_NAME = "anime-list.json"
CONFIG_ROOT = os.path.expanduser("~/.config/aminebot")
config = {}
shows = {}


class Message:
    def __init__(self, message="", embed="", link=""):
        self.message = message
        self.embed = embed
        self.link = link


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
    config = json.load(open(os.path.join(CONFIG_ROOT, "config.json")))
    shows = json.load(open(os.path.join(CONFIG_ROOT, "shows.json")))

    if "MAL_CLIENT_ID" not in config:
        exit("Must have MAL_CLIENT_ID in config!")
    if "MAL_CLIENT_SECRET" not in config:
        exit("Must have MAL_CLIENT_SECRET in config!")
    token = json.load(open(os.path.join(CONFIG_ROOT, TOKEN_NAME)))
    config["token"] = token

    for show in shows:
        if "previous_date" in shows[show]:
            shows[show]["previous_date"] = SerializableDatetime.fromisoformat(shows[show]["previous_date"])
        else:
            shows[show]["previous_date"] = SerializableDatetime(1970, 1, 1, tzinfo=JAPAN)

        if "skipped" not in shows[show]:
            shows[show]["skipped"] = 0

    return config

def SaveConfig():
    json.dump(config, open(os.path.join(CONFIG_ROOT, "config.json"), 'w'), default=lambda x: x.ToDict(), indent=2)

def SaveShows():
    json.dump(shows, open(os.path.join(CONFIG_ROOT, "shows.json"), 'w'), default=lambda x: x.ToDict(), indent=2)

def get_new_code_verifier():
    token = secrets.token_urlsafe(100)
    return token[:128]


def print_new_authorisation_url(code_challenge:str):
    global MAL_CLIENT_ID, MAL_CLIENT_SECRET

    url = f'https://myanimelist.net/v1/oauth2/authorize?response_type=code&MAL_client_id={MAL_CLIENT_ID}&code_challenge={code_challenge}'
    print(f'Authorise your application by clicking here: {url}\n')

# 3. Once you've authorised your application, you will be redirected to the webpage you've
#    specified in the API panel. The URL will contain a parameter named "code" (the Authorisation
#    Code). You need to feed that code to the application.
def generate_new_token(authorisation_code: str, code_verifier: str) -> dict:
    global MAL_CLIENT_ID, MAL_CLIENT_SECRET

    url = 'https://myanimelist.net/v1/oauth2/token'
    data = {
        'MAL_client_id': MAL_CLIENT_ID,
        'MAL_client_secret': MAL_CLIENT_SECRET,
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
    url = "https://myanimelist.net/v1/oauth2/token"

    data = {
            "MAL_client_id": config["MAL_CLIENT_ID"],
            "MAL_client_secret": config["MAL_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
    }

    response = requests.post(url, data=data)
    response.raise_for_status()

    token = response.json()
    response.close()
    print("Token refreshed successfully!")

    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'w') as file:
        json.dump(token, file, indent = 4)
        print('Token saved in "token.json"')

    token["aquired"] = now()
    return token


def retrieve_token():
    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'r') as file:
        return json.loads(file.read())


def save_token():
    temp = token["aquired"]
    token["aquired"] = repr(temp)
    with open('/'.join([CONFIG_ROOT, TOKEN_NAME]), 'w') as file:
        file.write(json.dumps(token))
    token["aquired"] = temp
    pass

#endregion

if __name__ == "__main__":
    ReadConfig()

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


    if (now() - config["token"]["aquired"]).days >= 30:
        config["token"] = refresh_token(config["token"]["refresh_token"])
        save_token()

    messages = []
    updated = check_for_updates()
    for id in updated:
        # Get the previous date and nickname
        show = shows[id]
        # Get rest of info
        info = mal.get_anime_info(config["token"]["access_token"], id)
        name = show["nickname"] if "nickname" in show else info["title"]

        # convert start date + broadcast time to datetime
        start_date = SerializableDatetime.fromisoformat(info["start_date"])
        hh, mm = info["broadcast"]["start_time"].split(":")
        start_date = start_date.replace(hour=int(hh), minute=int(mm), tzinfo=JAPAN)

        # Get current time
        current_date = now(JAPAN)

        # Find latest episode number
        diff = current_date - start_date
        SECONDS_IN_WEEK = 3600 * 24 * 7 - 120 # Tweak this by just a couple minutes
        floating = diff.total_seconds() / SECONDS_IN_WEEK
        episode_num = ceil(floating) - show["skipped"]

        print(name, floating, episode_num, start_date, current_date, "\n", sep="\n")

        # Skip unaired shows
        if episode_num < 1:
            continue

        # embed=info['main_picture']['medium']
        m = Message(link=f"https://myanimelist.net/anime/{id}")

        if info["num_episodes"] > 0 and episode_num > info["num_episodes"]:
            # Create a message for ended shows
            m.message = f"{name} has ended after {info['num_episodes']} episodes."

        else:
            # Create message for new episode
            print("New ep!")
            m.message = f"""{name} episode #{episode_num} is out!"""
            m.link += "\n<https://nyaa.si/?f=0&c=0_0&q=" + urllib.parse.quote(info["title"]) + ">"
            increment_previous_datetime(id)

        messages.append(m)

    if "--test" in sys.argv:
        exit()
    elif updated:
        # Save back to file
        SaveShows()
    else:
        exit()

    import discord_side
    token = config["DISCORD_TOKEN"]
    discord_side.begin(messages, token)
