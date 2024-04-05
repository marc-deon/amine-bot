import requests

# curl 'https://api.myanimelist.net/v2/anime/30230?fields=id
# ,title
# ,main_picture
# ,alternative_titles
# ,start_date
# ,end_date
# ,synopsis
# ,mean
# ,rank
# ,popularity
# ,num_list_users
# ,num_scoring_users
# ,nsfw
# ,created_at
# ,updated_at
# ,media_type
# ,status
# ,genres
# ,my_list_status
# ,num_episodes
# ,start_season
# ,broadcast
# ,source
# ,average_episode_duration
# ,rating
# ,pictures
# ,background
# ,related_anime
# ,related_manga
# ,recommendations
# ,studios
# ,statistics'

def get_anime_info(access_token:str, id:int,fields=["title", "num_episodes", "start_date", "broadcast"]):
    url = f'https://api.myanimelist.net/v2/anime/{id}?fields=' + ",".join(fields)
    response = requests.get(url, headers = {
        'Authorization': f"Bearer {access_token}",
    })
    response.raise_for_status()
    x = response.json()
    response.close()
    return x