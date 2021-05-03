import os
import win32api
import requests
import hashlib
import sys
from packaging import version
import re
import logging
from tabulate import tabulate
import json

logging.basicConfig(level=logging.INFO)

ModSaberAPI = "https://beatmods.com/api/v1/mod"
mods = []
config = None

try:
    with open('config.json') as config_file:
        config = json.load(config_file)
except IOError:
    print("Error opening config file")
    exit(1)

class Mod:
    md5 = None
    beatmods_name = None
    version_installed = None
    version_beatmods = None
    version_github = None
    github_username = None
    github_reponame = None

    def __init__(self, filename):
        self.filename = filename
        self.complete_path = config["BeatSaber_path"] + "\\Plugins\\" + self.filename

        with open(self.complete_path, 'rb') as file:
            self.md5 = hashlib.md5(file.read()).hexdigest()
            print(self.md5)

        self.version_installed = ".".join([str(i) for i in get_file_version(self.complete_path)])
        print(self.version_installed)


def get_file_version(path):
    info = win32api.GetFileVersionInfo(path, '\\')
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    return (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))


if __name__ == '__main__':
    BeatSaber_Plugin_path = config["BeatSaber_path"] + "\\Plugins"

    r = requests.get(url=ModSaberAPI)
    mods_json = r.json()

    for filename in os.listdir(BeatSaber_Plugin_path):
        if not filename.endswith(".dll"):
            continue

        current_mod = Mod(filename)

        mods.append(current_mod)

        mod_from_list = None
        mod_from_list_unapproved = None
        mod_from_list_file = None
        mod_from_list_file_unapproved = None

        # Search for approved mods via MD5
        for mod in mods_json:
            for downloads in mod["downloads"]:
                for hashes in downloads["hashMd5"]:
                    if hashes["hash"] == current_mod.md5:
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

        current_mod.beatmods_name = mod_from_list["name"]
        print(current_mod.beatmods_name+" ("+mod_from_list["version"]+")")


        newest_mod_from_list = mod_from_list

        for mod in mods_json:
            if mod["status"] != "approved":
                continue

            if mod["name"] == mod_from_list["name"]:
                if newest_mod_from_list is None or version.parse(mod["version"]) > version.parse(newest_mod_from_list["version"]):
                    newest_mod_from_list = mod

        current_mod.version_beatmods = newest_mod_from_list["version"]
        print(current_mod.version_beatmods)

        if version.parse(current_mod.version_installed) == version.parse(newest_mod_from_list["version"]):
            print("ModAssistant: Newest version installed")
        elif version.parse(current_mod.version_installed) > version.parse(newest_mod_from_list["version"]):
            print("ModAssistant: Newer version installed than on list")
        else:
            print("ModAssistant: Update available")

        newest_mod_from_list_link = newest_mod_from_list["link"]

        if newest_mod_from_list_link[-1] == "/":
            newest_mod_from_list_link = newest_mod_from_list_link[0:-1]

        print(newest_mod_from_list_link)

        link_parts = newest_mod_from_list_link.split('/')

        #if(len(link_parts))

        if not link_parts[-3] == "github.com":
            print("No github url found")
            print(newest_mod_from_list_link)
            continue

        github_username = link_parts[-2]
        github_reponame = link_parts[-1]

        print(github_username)
        print(github_reponame)

        # Fix weird entries
        # e.g. https://github.com/kinsi55/CS_BeatSaber_Camera2#camera2
        current_mod.github_username = github_username.split('#')[0]
        current_mod.github_reponame = github_reponame.split('#')[0]

        response = requests.get("https://api.github.com/repos/"+current_mod.github_username+"/"+current_mod.github_reponame+"/releases")
        response_json = response.json()

        if len(response_json) == 0:
            print("No latest release found")
            continue

        print(response_json[0]["tag_name"])

        match = re.findall(r'(\d+(?:\.\d+)+)', response_json[0]["tag_name"])

        if len(match) == 0:
            print('Failed to match github version number')
            continue

        github_version_string = match[0]
        current_mod.version_github = github_version_string
        print(current_mod.version_github)

        if version.parse(current_mod.version_installed) == version.parse(github_version_string):
            print("GitHub: Newest version installed")
        elif version.parse(current_mod.version_installed) > version.parse(github_version_string):
            print("GitHub: Newer version installed than on list")
        else:
            print("GitHub: Update available")

    tabulate_list = []
    for mod in mods:
        mod_append = []
        #print(mod.filename)
        mod_append.append(mod.filename)
        mod_append.append(mod.beatmods_name)
        if mod.github_username is not None and mod.github_reponame is not None:
            mod_append.append("https://github.com/"+mod.github_username+"/"+mod.github_reponame)
        else:
            mod_append.append("")
        mod_append.append(mod.version_installed)
        mod_append.append(mod.version_beatmods)
        mod_append.append(mod.version_github)

        tabulate_list.append(mod_append)

    print(tabulate(tabulate_list))
