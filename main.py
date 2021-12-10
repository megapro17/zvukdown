import sys
import requests
import os
import time
from mutagen.flac import FLAC, Picture
VERIFY = True

headers = {
    #"x-auth-token": "lyBynraXP7wS1IWWwYU9c2wsB4HSUYU7"
    "x-auth-token": "p7REJnkfNeWZLTaPJg0f9XEkPk3FXhdf"
}

def ntfs(folder):
    for ch in ['<', '>', ':', '"', '/', '\\', '|', '?', '*']:
        if ch in folder:
            folder = folder.replace(ch, " ")
    folder = " ".join(folder.split())
    folder = folder.replace(" .flac", ".flac")
    return folder


def get_copyright(label_id):
    url = f"https://zvuk.com/api/tiny/labels?ids={label_id}"
    r = requests.get(url, verify=VERIFY)
    if r.status_code != 200:
        raise Exception('get_copyright not 200')
    resp = r.json(strict=False)
    a = resp['result']['labels']
    a = list(a.values())[0]
    return(a['title'])


def get_track_ids(album_id):
    url = f"https://zvuk.com/api/tiny/releases?ids={album_id}"

    r = requests.get(url, verify=VERIFY)
    if r.status_code != 200:
        raise Exception('releases not 200')

    resp = r.json(strict=False)
    a = resp['result']['releases']
    a = list(a.values())[0]

    cp = get_copyright(a['label_id'])

    return [a['track_ids'], cp, a['date']]


def download(track_id):
    print(track_id)
    url = f"https://zvuk.com/api/tiny/track/stream?id={track_id}&quality=flac"

    r = requests.get(url, headers=headers, verify=VERIFY)
    if r.status_code != 200:
        raise Exception('download not 200')

    resp = r.json(strict=False)
    time.sleep(1)
    return resp['result']['stream']


def get_info(track_ids, date):
    url = f"https://zvuk.com/api/tiny/tracks?ids={str(track_ids).strip('[]')}"
    r = requests.get(url, headers=headers, verify=VERIFY)
    if r.status_code != 200:
        raise Exception('info not 200')

    resp = r.json(strict=False)
    info = []
    for i, s in enumerate(resp['result']['tracks'].items()):
        if s[1]['has_flac'] != "true":
            if s[1]['highest_quality'] != "flac":
                raise Exception('has_flac, but highest_quality is not flac, token is invalid')
            author = s[1]['credits']
            name = s[1]['title']
            album = s[1]['release_title']
            release_id = s[1]['release_id']
            track_id = s[1]['id']
            tracknumber = i + 1
            if s[1]['genres']:
                genre = s[1]['genres'][0]
            else:
                genre = ""

            image = s[1]['image']['src'].replace(r"&size={size}&ext=jpg", "")
            link = download(s[0])

            info.append({
                "author": author, "name": name, "album": album, "release_id": release_id, "track_id": track_id, "genre": genre, "tracknumber": tracknumber, "date": date, "image": image, "link": link
            })
        else:
            print(f"Skipping track {s[1]['title']}, no flac")
    return info


def download_album(i, cp=""):
    i = info[0]
    if len(info) != 1:
        folder = f'{i["author"]} - {i["album"]} ({str(i["date"])[0:4]})'
        folder = ntfs(folder)
        if not os.path.exists(folder):
            os.makedirs(folder)
        else:
            print("Folder already exist, continue?")
            a = input()
            if not a:
                os._exit()
        os.chdir(folder)
    r = requests.get(i["image"], allow_redirects=True, verify=VERIFY)
    open("cover.jpg", 'wb').write(r.content)
    print("Optimizing png")
    os.system("pingo -strip -sa cover.jpg")
    for i in info:
        if len(info) != 1:
            filename = f'{i["tracknumber"]:02d} - {i["name"]}.flac'
        else:
            filename = f'{i["author"]} - {i["name"]}.flac'

        filename = ntfs(filename)

        r = requests.get(i["link"], allow_redirects=True, verify=VERIFY)
        open(filename, 'wb').write(r.content)

        # Loading a flac file
        audio = FLAC(filename)
        audio["ARTIST"] = i["author"]
        audio["TITLE"] = i["name"]
        audio["ALBUM"] = i["album"]
        if len(info) != 1:
            audio["TRACKNUMBER"] = str(i["tracknumber"])
            audio["TRACKTOTAL"] = str(len(info))


        audio["GENRE"] = i["genre"]
        audio["COPYRIGHT"] = cp
        audio["DATE"] = str(i["date"])
        audio["YEAR"] = str(i["date"])[0:4]
        
        
        #audio["DATE"] = str(i["date"])
        #audio["RELEASED"] = str(i["date"])
        #audio["YEAR"] = str(i["date"])[0:4]
        #audio["COPYRIGHT"] = f"release_id: {i[3]}, track_id: {i[4]}"
        
        audio["RELEASE_ID"] = str(i["release_id"])
        audio["TRACK_ID"] = str(i["track_id"])

        covart = Picture()
        covart.data = open("cover.jpg", 'rb').read()
        covart.type = 3  # as the front cover
        covart.mime = "image/jpeg"
        audio.add_picture(covart)

        # Printing the metadata
        print(audio.pprint() + '\n')

        # Saving the changes
        audio.save()
        time.sleep(1)
    if len(info) == 1:
        os.remove("cover.jpg")

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] != '--release':
        print(f"Download album:")
        print(f"{sys.argv[0]} --release release_id")
        print(f"{sys.argv[0]} https://sber-zvuk.com/release/4881970")
        print()
        print("Download one track from album:")
        print(f"{sys.argv[0]} --release release_id --track track_id")
        print(f"{sys.argv[0]} --release https://sber-zvuk.com/release/4881970 --track https://sber-zvuk.com/track/47115492")
    else:

        print("Getting tracks_ids")
        track_ids, cp, date = get_track_ids(sys.argv[2].strip(r"https://sber-zvuk.com/release/"))
        if len(sys.argv) > 3 and sys.argv[3] == '--track':
            track_ids = sys.argv[4].strip(r"https://sber-zvuk.com/track/")

        print("Getting info")
        info = get_info(track_ids, date)

        print("Downloading")
        download_album(info, cp)

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
