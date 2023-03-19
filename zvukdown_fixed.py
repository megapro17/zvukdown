import glob
import os
import subprocess
import sys
import time
from pathlib import Path
from shutil import copyfile
from typing import Any

import requests
from mutagen.flac import FLAC, Picture

class zvukdown_:        
    def __init__(self):
        self.verify = True
        self.headers = []
        # self.token = self.read_token()
        pass

    def read_token(self):
        import os.path
        if os.path.exists('token.txt'):
            with open("token.txt", "r", encoding="utf8") as f:
                token = f.read()
                if len(token) != 32:
                    raise Exception("Wrong token length")
                self.headers = {"x-auth-token": token}
        else:
            print('Нет файла token.txt')

    def save_token(self, login, password):
        url = "https://zvuk.com/api/tiny/login/email"
        params = {
            "register": "true"
        }
        data = {
            "email": login,
            "password": password,
        }
        r = requests.post(url, params=params, data=data, verify=self.verify)
        r.raise_for_status()
        resp = r.json(strict=False)
        if "result" in resp:
            if "token" in resp["result"]:
                with open("token.txt", "w", encoding="utf8") as f:
                    token = resp["result"]["token"]
                    f.write(token)
                    if len(token) != 32:
                        raise Exception("Wrong token length")
                    self.headers = {"x-auth-token": token}

    @staticmethod
    def __ntfs(filename):
        for ch in ['<', '>', '@', '%', '!', '+', ':', '"', '/', '\\', '|', '?', '*']:
            if ch in filename:
                filename = filename.replace(ch, "_")
        filename = " ".join(filename.split())
        filename = filename.replace(" .flac", ".flac")
        return filename

    @staticmethod
    def __launch(args):
        try:
            pipe = subprocess.Popen(args, creationflags=0x08000000, stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            output, err = pipe.communicate()
            pipe.wait()

            if pipe.returncode != 0:
                print(args + '\n')
                print(output + '\n')
                print(err)
                raise Exception("Unable to launch")
            return output
        except FileNotFoundError:
            return "Install pingo and imagemagick!"

    @staticmethod
    def __to_str(l):
        global int
        if isinstance(l, int):
            return [l]
        elif not isinstance(l, str):
            l = [str(int) for int in l]
            l = ",".join(l)
            l = str(l.strip('[]'))
        return l

    def __get_copyright(self, label_ids):
        label_ids = self.__to_str(label_ids)
        url = f"https://zvuk.com/api/tiny/labels"
        params = {
            "ids": label_ids
        }
        r = requests.get(url, params=params, verify=self.verify)
        r.raise_for_status()
        resp = r.json(strict=False)

        info = {}
        for i in resp['result']['labels'].values():
            info[i["id"]] = i['title']
        return (info)

    def __get_tracks_metadata(self, track_ids):
        track_ids = self.__to_str(track_ids)
        params = {
            "ids": track_ids
        }
        url = "https://zvuk.com/api/tiny/tracks"
        r = requests.get(url, params=params,
                         headers=self.headers, verify=self.verify)
        r.raise_for_status()
        resp = r.json(strict=False)
        info = {}
        for s in resp['result']['tracks'].values():
            if s['has_flac']:
                author = s['credits']
                name = s['title']
                album = s['release_title']
                release_id = s['release_id']
                track_id = s['id']
                if s['genres']:
                    # genre = s['genres'][0]
                    genre = ", ".join(s['genres'])
                else:
                    genre = ""

                number = s["position"]
                image = s['image']['src'].replace(r"&size={size}&ext=jpg", "")

                info[track_id] = {"author": author, "name": name, "album": album, "release_id": release_id,
                                  "track_id": track_id, "genre": genre, "number": number, "image": image}
            else:
                if s['highest_quality'] != "flac":
                    raise Exception(
                        "has_flac, but highest_quality is not flac, token is invalid")
                raise Exception(f"Skipping track {s['title']}, no flac")
        return info

    def __get_tracks_link(self, track_ids):
        links = {}
        print(" ")
        print("Поиск треков:")
        print(" ")
        index = 0
        for i in track_ids:
            url = "https://zvuk.com/api/tiny/track/stream"
            params = {
                "id": i,
                "quality": "flac"
            }
            r = requests.get(url, params=params,
                             headers=self.headers, verify=self.verify)
            # r.raise_for_status()
            # print(r.raise_for_status())
            resp = r.json(strict=False)
            links[i] = resp['result']['stream']
            if links[i] != 0:
                index += 1
                print(index,": ",i, "- ", resp['result']['stream'])
            time.sleep(3)
        return links

    def __get_releases_info(self, release_ids: object) -> object:
        release_ids = self.__to_str(release_ids)

        info = {}
        url = "https://zvuk.com/api/tiny/releases"
        params = {
            "ids": release_ids
        }
        r = requests.get(url, params=params,
                         headers=self.headers, verify=self.verify)
        r.raise_for_status()
        resp = r.json(strict=False)

        labels = set()
        for i in resp['result']["releases"].values():
            labels.add(i["label_id"])
        labels_info = self.__get_copyright(labels)

        # print(resp)
        for a in resp['result']["releases"].values():
            info[a["id"]] = {"track_ids": a["track_ids"], "tracktotal": len(a["track_ids"]),
                             "copyright": labels_info[a['label_id']], "date": a["date"], "album": a["title"],
                             "author": a["credits"]}
        # print(info)
        return info

    def __download_image(self, release_id, image_link):
        global err
        pic: Path = Path(f"temp_{release_id}.jpg")
        comp_pic = Path(f"temp_{release_id}_comp.jpg")
        if not pic.is_file():
            # os.system("pause")
            r = requests.get(image_link, allow_redirects=True,
                             verify=self.verify)
            open(pic, 'wb').write(r.content)
            # print(self.__launch(f'pingo -sa -notime -strip {pic}'))
            # if os.path.getsize(pic) > 2 * 1000 * 1000:
            # print(self.__launch(f"magick convert {pic} -define jpeg:extent=1MB {comp_pic}"))
            # print(self.__launch(f'pingo -sa -notime -strip {comp_pic}'))
            # else:
            # copyfile(pic, comp_pic)
        copyfile(pic, comp_pic)
        # pingo optimize, compress
        return {"original": pic, "compressed": comp_pic}
        # return {"original": pic}

    def __save_track(self, url, metadata, releases, single):
        pic = self.__download_image(metadata["release_id"], metadata["image"])
        if not single and releases["tracktotal"] != 1:
            folder = f'{releases["author"]} - {str(releases["date"])[0:4]} {releases["album"]}'
            folder = self.__ntfs(folder)
            if not os.path.exists(folder):
                os.makedirs(folder)
                copyfile(pic["original"], os.path.join(folder, "cover.jpg"))
            # else:
            #    print("Folder already exist, continue?")
            #    a = input()
            #    if not a:
            #        os._exit()
            # os.chdir(folder)
            pic = pic["compressed"]
            filename = f'{metadata["number"]:02d} - {metadata["name"]}.flac'
        else:
            pic = pic["original"]
            folder = ""
            filename = f'{metadata["author"]} - {metadata["name"]}.flac'
        
        filename = self.__ntfs(filename)
        filename = os.path.join(folder, filename)

        r = requests.get(url, allow_redirects=True, verify=self.verify)
        open(filename, 'wb').write(r.content)

        audio = FLAC(filename)
        audio["ARTIST"] = metadata["author"]
        audio["TITLE"] = metadata["name"]
        audio["ALBUM"] = metadata["album"]
        audio["TRACKNUMBER"] = str(metadata["number"])
        audio["TRACKTOTAL"] = str(releases["tracktotal"])

        audio["GENRE"] = metadata["genre"]
        audio["COPYRIGHT"] = releases["copyright"]
        audio["DATE"] = str(releases["date"])
        audio["YEAR"] = str(releases["date"])[0:4]

        audio["RELEASE_ID"] = str(metadata["release_id"])
        audio["TRACK_ID"] = str(metadata["track_id"])

        covart = Picture()
        covart.data = open(pic, 'rb').read()
        covart.type = 3  # as the front cover
        covart.mime = "image/jpeg"
        audio.add_picture(covart)

        # Printing the metadata
        print(audio.pprint() + '\n')

        # Saving the changes
        audio.save()
        time.sleep(1)

    def download_tracks(self, track_ids, single=False, releases=""):
        metadata = self.__get_tracks_metadata(track_ids)
        link = self.__get_tracks_link(track_ids)

        if len(metadata) != len(link):
            raise Exception("metadata != link")

        if not releases:
            release_ids = set()
            for i in metadata.values():
                release_ids.add(i["release_id"])
            releases = self.__get_releases_info(release_ids)

        print(" ")
        print("Скачивание треков")
        print(" ")
        index = 0
        for i in metadata.keys():
            print(" ")
            index += 1
            print("Скачивание трека № ", index, ":")
            self.__save_track(link[i], metadata[i],
                              releases[metadata[i]["release_id"]], single)

    def download_albums(self, release_ids):
        track_ids = []
        releases: dict[Any, dict[str, int | Any]] = self.__get_releases_info(release_ids)
        #print(releases)
        print(" ")
        print("Информация о релизе: \n")
        from pprint import pprint
        pprint(releases)
        #for key, value in releases.items():
        #    if key := track_ids:
        #        print(" ")
        #    else:
        #        print("{0}: {1}".format(key, value) + "\n")
        # os.system("pause")
        for i in releases.values():
            track_ids += i["track_ids"]
        self.download_tracks(track_ids, releases=releases)


if __name__ == '__main__':
    
    release_ids = []
    track_ids = []
    z = zvukdown_()

    if "login" in sys.argv:
        # print(sys.argv[2], sys.argv[3])
        z.save_token(sys.argv[2], sys.argv[3])
        print("Token saved!")
    else:
        if "debug" in sys.argv:
            z.verify = False
        for i in sys.argv:
            # print(i)
            if "release" in i:
                release_ids.append(int(i.strip("https://sber-zvuk.com/release/")))
            elif "track" in i:
                track_ids.append(int(i.strip("https://sber-zvuk.com/track/")))

        z.read_token()
        if release_ids:
            z.download_albums(release_ids)
        if track_ids:
            z.download_tracks(track_ids, True)
        list(map(os.remove, glob.glob("temp*.jpg")))
