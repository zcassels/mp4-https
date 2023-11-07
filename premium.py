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
search_res = res.json()

if len(search_res) > 1:
    raise Exception(f"Too many results for {search_term}")
if len(search_res) == 0:
    raise Exception(f"Could not find {search_term}")

series_id = search_res[0]['id']
series_title = search_res[0]['title']
series_path = search_res[0]['link'].lower()

res = requests.get(f'{base_url}{series_path}', headers=headers)

session_info_page = BeautifulSoup(res.text, 'html.parser')

# write to file for debugging
# with open("log.html", 'w') as http_log:
#     http_log.write(session_info_page.prettify())

if session_info_page.find("input", id="remember-me"):
    raise Exception("Got login page, could be a stale token?")

season_list_items = [int(item['data-season']) for item in session_info_page.find("div", class_="tv-details-seasons").find_all("li")]
filtered_seasons = [season for season in season_list_items if season_selection is None or season in season_selection]

for season_num in filtered_seasons: 
    res = requests.get(f'{base_url}/series/season?id={series_id}&s={season_num}&token={token}', headers=headers)
    episodes = res.json()
    for episode in episodes:
        episode_num = int(episode['episode_number'])
        # https://premium.gd/series/getTvLink?id=705&token=00cae1e781faadad4ab3fef30e0b15c4&s=0&e=177&oPid=&_=1699320564869
        media_res = requests.get(f'https://premium.gd/series/getTvLink?id={series_id}&token={token}&s={season_num}&e={episode_num}', headers=headers)

        media_url = media_res.json()['jwplayer'][0]['file']
        media_url = media_url.replace("http://sv1.", "http://sv2.")
        # url = media_url.replace('trial1.premium.gd', 'sv2.premium.gd').replace("http:", "https:")

        file_name = media_url.split("/")[-1].split("?")[0]
        title_path = series_title.replace(" ", "_")
        output_dir = f"{media_path}{title_path}/session_{season_num}"
        output_path = f"{output_dir}/{file_name}"

        if os.path.exists(output_path):
            print(f"{output_path} already exists")
            continue

        os.makedirs(output_dir, exist_ok=True)

        # http://sv2.premium.gd/tv/tt2861424/s0e177_720p.mp4?st=Ut4rWGJIU4KrRH6FWAmJig&e=1699311009&end=610
        # https://sv1.premium.gd/tv/tt2861424/s0e177_720p.mp4?st=WHFiar1sfochyy-3GQx-gQ&e=1699311077&u=55844' -o somefile.mp4

        curl_cmd = f"{curl_path} \"{media_url}\" -o {output_path}"
        print(curl_cmd)
        print(f"fetching {series_title} Session {season_num} Ep {episode_num} {output_path}")
        os.system(curl_cmd)

        # check if operation was successful
        if os.path.exists(output_path):
            print(f"Successfully Downloaded {output_path}")
        else:
            print(f"failed to Downloaded {output_path}!")

        # https://sv1.premium.gd/ = Germany
        # https://sv2.premium.gd/ = DC