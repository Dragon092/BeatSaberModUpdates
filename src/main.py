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
from github import Github, RateLimitExceededException

logging.basicConfig(level=logging.INFO)

ModSaberAPI = "https://beatmods.com/api/v1/mod"
mods = []
config = None
github = Github()
disable_github = False

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
        self.complete_path = config["BeatSaber_path"] + "/Plugins/" + self.filename

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


def github_url_to_parts(url):
    if url[-1] == "/":
        url = url[0:-1]

    print(url)

    link_parts = url.split('/')

    if len(link_parts) < 3:
        print("Url split too short")
        return None, None

    if not link_parts[-3] == "github.com":
        print("No github url found")
        print(url)
        return None, None

    github_username = link_parts[-2]
    github_reponame = link_parts[-1]

    # Fix weird entries
    # e.g. https://github.com/kinsi55/CS_BeatSaber_Camera2#camera2
    github_username = github_username.split('#')[0]
    github_reponame = github_reponame.split('#')[0]

    print(github_username)
    print(github_reponame)

    return github_username, github_reponame


if __name__ == '__main__':
    BeatSaber_Plugin_path = config["BeatSaber_path"] + "/Plugins"

    print("You BeatSaber path is set to:")
    print(config["BeatSaber_path"])
    print("Scanning for mods in:")
    print(BeatSaber_Plugin_path)

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
                            # We found a approved mod with the exact hash
                            mod_from_list = mod
                            break
                        elif mod_from_list_unapproved is None:
                            # We found any mod with the exact hash
                            mod_from_list_unapproved = mod

                    if hashes["file"] == "Plugins/" + filename:
                        if mod["status"] == "approved" and mod_from_list_file is None:
                            # We found a approved mod with the filename
                            mod_from_list_file = mod
                        elif mod_from_list_file_unapproved is None:
                            # We found any mod with the filename
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
        print("Found BeatMods: "+current_mod.beatmods_name+" ("+mod_from_list["version"]+")")


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
            print("BeatMods: Newest version installed")
        elif version.parse(current_mod.version_installed) > version.parse(newest_mod_from_list["version"]):
            print("BeatMods: Newer version installed than on list")
        else:
            print("BeatMods: Update available")

        current_mod.github_username, current_mod.github_reponame = github_url_to_parts(newest_mod_from_list["link"])

        if current_mod.github_username is None or current_mod.github_reponame is None:
            print("No GitHub names found")
            continue

        if disable_github:
            print("Checking GitHub is diabled for this run")
            continue

        try:
            github_repository = github.get_repo(current_mod.github_username+"/"+current_mod.github_reponame)
            releases = github_repository.get_releases()

            if releases.totalCount == 0:
                print("No latest release found")
                continue

            print(releases[0].tag_name)

            match = re.findall(r'(\d+(?:\.\d+)+)', releases[0].tag_name)

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
        except RateLimitExceededException:
            print("GitHub RateLimitExceededException, you need to wait 60 minutes to try again")
            disable_github = True
            continue

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
