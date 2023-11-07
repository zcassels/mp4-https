import requests
from bs4 import BeautifulSoup
import os
import argparse
import shutil

# TOKEN is extracted from the PHPSESSID key in the website cookie
token = os.environ['TOKEN']

parser = argparse.ArgumentParser(prog='PremiumGettr', description='Downloads episodes from premium.gd')

parser.add_argument('-n', '--name', required=True)
parser.add_argument('-m', '--media-path', default="./")

# series or movies
parser.add_argument('-t', '--type', default=None)
parser.add_argument('-y', '--year', default=None)
parser.add_argument('-s', '--seasons')

args = parser.parse_args()

curl_path = "curl"
if os.name == "nt":
    curl_path = "c:/WINDOWS/system32/curl"

search_term = args.name
if args.seasons is not None:
    season_selection = [int(s) for s in args.seasons.split(",")]
else:
    season_selection = None

if not os.path.exists(args.media_path):
    raise Exception(f"Bad media path {args.media_path}")

media_path = args.media_path

if shutil.which("curl") is None:
    raise Exception("Must have cURL binary, can use Cygwin")

headers = {
    'Cookie': f'PHPSESSID={token};',
    'authority': 'premium.gd'
}

base_url = 'https://premium.gd'

# make season selection zero-based
if season_selection:
    season_selection = [selection for selection in season_selection]

# https://premium.gd/series
query = {
    'q': search_term
}
res = requests.get(f'{base_url}/search/auto', params=query, headers=headers)

def filter_media(res, year, type):
    if year is not None and year != res['year']:
        return
    if type is not None and type != res['link'].split("/")[1]:
        pass
    return res

def download_media(curl_path, url, output_path):
    curl_cmd = f"{curl_path} \"{url}\" -o {output_path}"
    print(curl_cmd)
    
    os.system(curl_cmd)

    # check if operation was successful
    if os.path.exists(output_path):
        print(f"Successfully Downloaded {output_path}")
    else:
        print(f"failed to Downloaded {output_path}!")

search_res = [s for s in res.json() if filter_media(s, args.year, args.type)]

if len(search_res) == 0:
    raise Exception(f"Could not find {search_term}")
if len(search_res) > 1:
    raise Exception("too many results, filter results")


id = search_res[0]['id']
title = search_res[0]['title']
link = search_res[0]['link'].lower()
type = search_res[0]['link'].split("/")[1]

if type == "movies":
    
    move_res = requests.get(f"https://premium.gd/movies/getMovieLink?id={id}&token={token}", headers=headers)
    media_info = move_res.json()
    dl_url = media_info['dl']
    if 'dl_hd' in media_info:
        dl_url = media_info['dl_hd']
    file_name = dl_url.split("/")[-1].split("?")[0]
    output_path = f"{media_path}/{file_name}"

    if os.path.exists(output_path):
        print(f"{output_path} already exists")
    else:
        print(f"fetching {title} Movie {output_path}")
        download_media(curl_path, dl_url, output_path)



elif type == "series":

    res = requests.get(f'{base_url}{link}', headers=headers)

    session_info_page = BeautifulSoup(res.text, 'html.parser')

    # write to file for debugging
    # with open("log.html", 'w') as http_log:
    #     http_log.write(session_info_page.prettify())

    if session_info_page.find("input", id="remember-me"):
        raise Exception("Got login page, could be a stale token?")

    season_list_items = [int(item['data-season']) for item in session_info_page.find("div", class_="tv-details-seasons").find_all("li")]
    filtered_seasons = [season for season in season_list_items if season_selection is None or season in season_selection]

    for season_num in filtered_seasons: 
        res = requests.get(f'{base_url}/series/season?id={id}&s={season_num}&token={token}', headers=headers)
        episodes = res.json()
        for episode in episodes:
            episode_num = int(episode['episode_number'])
            # https://premium.gd/series/getTvLink?id=705&token=00cae1e781faadad4ab3fef30e0b15c4&s=0&e=177&oPid=&_=1699320564869

            media_res = requests.get(f'https://premium.gd/series/getTvLink?id={id}&token={token}&s={season_num}&e={episode_num}', headers=headers)
            
            media_info = media_res.json()
            media_url = media_info['jwplayer'][0]['file']
            dl_url = media_info['dl']
            if 'dl_hd' in media_info:
                dl_url = media_info['dl_hd']
            
            file_name = dl_url.split("/")[-1].split("?")[0]
            title_path = title.replace(" ", "_")
            output_dir = f"{media_path}{title_path}/session_{season_num}"
            output_path = f"{output_dir}/{file_name}"

            if os.path.exists(output_path):
                print(f"{output_path} already exists")
                continue

            os.makedirs(output_dir, exist_ok=True)

            print(f"fetching {title} Session {season_num} Ep {episode_num} {output_path}")
            download_media(curl_path, dl_url, output_path)
else:
    raise Exception(f"Unknown media type {type}")

