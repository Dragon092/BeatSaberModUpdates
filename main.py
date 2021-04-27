import os
import win32api
import requests
import hashlib
import sys
from packaging import version
import re

BeatSaber_path = "G:\SteamLibrary\steamapps\common\Beat Saber"
ModSaberAPI = "https://beatmods.com/api/v1/mod"


def get_file_version(path):
    info = win32api.GetFileVersionInfo(path, '\\')
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    return (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))


if __name__ == '__main__':
    BeatSaber_Plugin_path = BeatSaber_path + "\Plugins"

    r = requests.get(url=ModSaberAPI)
    mods_json = r.json()

    for filename in os.listdir(BeatSaber_Plugin_path):
        if not filename.endswith(".dll"):
            continue

        complete_path = BeatSaber_Plugin_path + "\\" + filename

        print(complete_path)

        with open(complete_path, 'rb') as file:
            mod_md5 = hashlib.md5(file.read()).hexdigest()
            print(mod_md5)

        dll_version = ".".join([str(i) for i in get_file_version(complete_path)])
        print(dll_version)

        mod_from_list = None
        mod_from_list_unapproved = None
        mod_from_list_file = None
        mod_from_list_file_unapproved = None

        # Search for approved mods via MD5
        for mod in mods_json:
            for downloads in mod["downloads"]:
                for hashes in downloads["hashMd5"]:
                    if hashes["hash"] == mod_md5:
                        if mod["status"] == "approved":
                            mod_from_list = mod
                            break
                        elif mod_from_list_unapproved is None:
                            mod_from_list_unapproved = mod

                    if hashes["file"] == "Plugins/" + filename:
                        if mod["status"] == "approved" and mod_from_list_file is None:
                            mod_from_list_file = mod
                        elif mod_from_list_file_unapproved is None:
                            mod_from_list_file_unapproved = mod

        if not mod_from_list:
            if mod_from_list_file:
                mod_from_list = mod_from_list_file
            elif mod_from_list_unapproved:
                mod_from_list = mod_from_list_unapproved
            elif mod_from_list_file_unapproved:
                mod_from_list = mod_from_list_file_unapproved

        if not mod_from_list:
            print("Still not found...")
            continue

        print(mod_from_list["name"]+" ("+mod_from_list["version"]+")")


        newest_mod_from_list = None

        for mod in mods_json:
            if mod["name"] == mod_from_list["name"]:
                if newest_mod_from_list is None or version.parse(mod["version"]) > version.parse(newest_mod_from_list["version"]):
                    newest_mod_from_list = mod

        print(newest_mod_from_list["version"])

        if version.parse(dll_version) == version.parse(newest_mod_from_list["version"]):
            print("Newest version installed")
        elif version.parse(dll_version) > version.parse(newest_mod_from_list["version"]):
            print("Newer version installed than on list")
        else:
            print("Update available")

        newest_mod_from_list_link = newest_mod_from_list["link"]

        if newest_mod_from_list_link[-1] == "/":
            newest_mod_from_list_link = newest_mod_from_list_link[0:-1]

        print(newest_mod_from_list_link)

        link_parts = newest_mod_from_list_link.split('/')

        #if(len(link_parts))

        if not link_parts[-3] == "github.com":
            print("No github url found")
            print(newest_mod_from_list_link)
            sys.exit(1)
            continue

        github_username = link_parts[-2]
        github_reponame = link_parts[-1]

        print(github_username)
        print(github_reponame)

        # Fix weird entries
        # e.g. https://github.com/kinsi55/CS_BeatSaber_Camera2#camera2
        github_username = github_username.split('#')[0]
        github_reponame = github_reponame.split('#')[0]

        response = requests.get("https://api.github.com/repos/"+github_username+"/"+github_reponame+"/releases")

        response_json = response.json()

        if len(response_json) == 0:
            print("No latest release found")
            continue

        print(response_json[0]["name"])

        match = re.findall(r'(\d+(?:\.\d+)+)', response_json[0]["name"])

        if len(match) == 0:
            print('Failed to match github version number')
            continue

        github_version_string = match[0]
        print(github_version_string)

        if version.parse(dll_version) == version.parse(github_version_string):
            print("Newest version installed")
        elif version.parse(dll_version) > version.parse(github_version_string):
            print("Newer version installed than on list")
        else:
            print("Update available")
