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
from json import JSONDecodeError
from github import Github, RateLimitExceededException
from urllib.parse import urlparse
from pprint import pprint
import colorama

logging.basicConfig(level=logging.WARNING)

BeatModsAPI = "https://beatmods.com/api/v1/mod"
mods = []
config = None
disable_github = False

try:
    with open('config.json') as config_file:
        config_file_content = config_file.read()
        # Allow backslashes in the config file without raising an error
        config_file_content = config_file_content.replace("\\", "/")
        config = json.loads(config_file_content)
except IOError:
    logging.error("Error opening config.json file")
    input("press enter to exit")
    exit(1)
except JSONDecodeError:
    logging.error("Error reading config.json file")
    input("press enter to exit")
    exit(1)

# Fix config values
if config["GitHub_Token"] == "":
    config["GitHub_Token"] = None

github = Github(config["GitHub_Token"])


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
            logging.debug("md5: "+self.md5)

        self.version_installed = ".".join([str(i) for i in get_file_version(self.complete_path)])
        logging.debug("version_installed: "+self.version_installed)


def get_file_version(path):
    info = win32api.GetFileVersionInfo(path, '\\')
    ms = info['FileVersionMS']
    ls = info['FileVersionLS']
    return (win32api.HIWORD(ms), win32api.LOWORD(ms), win32api.HIWORD(ls), win32api.LOWORD(ls))


def github_url_to_parts(url):

    logging.debug("url: "+url)

    url_parsed = urlparse(url)

    logging.debug("url_parsed.path: "+url_parsed.path)
    link_parts = url_parsed.path.split("/")

    if not url_parsed.netloc == "github.com":
        logging.error("No github url found")
        logging.error(url)
        return None, None

    if len(link_parts) < 2:
        logging.error("Url split too short")
        return None, None

    # link_parts[0] is empty because the string start with a /
    github_username = link_parts[1]
    github_reponame = link_parts[2]

    logging.debug("github_username: "+github_username)
    logging.debug("github_reponame: "+github_reponame)

    return github_username, github_reponame


if __name__ == '__main__':
    BeatSaber_Plugin_path = config["BeatSaber_path"] + "/Plugins"

    print("You BeatSaber path is set to:")
    print(config["BeatSaber_path"])
    print("Scanning for mods in:")
    print(BeatSaber_Plugin_path)

    r = requests.get(url=BeatModsAPI)
    mods_json = r.json()

    if not os.path.exists(BeatSaber_Plugin_path):
        logging.error("Error opening plugin path, please make sure that you have set the correct path to your BeatSaber installation in the config.json file")
        input("press enter to exit")
        exit(1)

    for filename in os.listdir(BeatSaber_Plugin_path):
        if not filename.endswith(".dll"):
            #logging.debug("Ignoring "+filename)
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
            logging.warning("Could not find a matching BeatMods entry for "+filename)
            continue

        current_mod.beatmods_name = mod_from_list["name"]
        logging.info("Found BeatMods: "+current_mod.beatmods_name+" ("+mod_from_list["version"]+")")


        newest_mod_from_list = mod_from_list

        for mod in mods_json:
            if mod["status"] != "approved":
                continue

            if mod["name"] == mod_from_list["name"]:
                if newest_mod_from_list is None or version.parse(mod["version"]) > version.parse(newest_mod_from_list["version"]):
                    newest_mod_from_list = mod

        current_mod.version_beatmods = newest_mod_from_list["version"]
        logging.info("Found newest BeatMods version: "+current_mod.version_beatmods)

        if version.parse(current_mod.version_installed) == version.parse(newest_mod_from_list["version"]):
            logging.info("BeatMods: Newest version installed")
        elif version.parse(current_mod.version_installed) > version.parse(newest_mod_from_list["version"]):
            logging.info("BeatMods: Newer version installed than on list")
        else:
            logging.info("BeatMods: Update available")

        current_mod.github_username, current_mod.github_reponame = github_url_to_parts(newest_mod_from_list["link"])

        if current_mod.github_username is None or current_mod.github_reponame is None:
            logging.warning("No GitHub names found")
            continue

        if disable_github:
            logging.warning("Checking GitHub is diabled for this run")
            continue

        try:
            github_repository = github.get_repo(current_mod.github_username+"/"+current_mod.github_reponame)
            releases = github_repository.get_releases()

            if releases.totalCount == 0:
                logging.warning("No latest release found")
                continue

            logging.debug(releases[0].tag_name)

            match = re.findall(r'(\d+(?:\.\d+)+)', releases[0].tag_name)

            if len(match) == 0:
                logging.warning("Failed to match github version number: "+releases[0].tag_name)
                continue

            github_version_string = match[0]
            current_mod.version_github = github_version_string
            logging.debug("version_github: "+current_mod.version_github)

            if version.parse(current_mod.version_installed) == version.parse(github_version_string):
                logging.info("GitHub: Newest version installed")
            elif version.parse(current_mod.version_installed) > version.parse(github_version_string):
                logging.info("GitHub: Newer version installed than on list")
            else:
                logging.info("GitHub: Update available")
        except RateLimitExceededException:
            logging.error("GitHub RateLimitExceededException, you need to wait 60 minutes to try again")
            disable_github = True
            continue

    if disable_github:
        logging.warning("---")
        logging.warning("WARNING: GitHub rate limit reached during scan, so GitHub versions will be (partialy) missing.")
        logging.warning("You need to wait 60 minutes for the limit to reset or set a GitHub API token in the config.")
        logging.warning("---")

    # Generate output
    tabulate_list = []
    for mod in mods:
        mod_append = []
        #logging.debug(mod.filename)
        mod_append.append(mod.filename)
        mod_append.append(mod.beatmods_name)
        if mod.github_username is not None and mod.github_reponame is not None:
            mod_append.append("https://github.com/"+mod.github_username+"/"+mod.github_reponame)
        else:
            mod_append.append("")

        mod_append.append(colorama.Back.GREEN + mod.version_installed + colorama.Back.RESET)

        if not mod.version_beatmods is None:
            if version.parse(mod.version_installed) >= version.parse(mod.version_beatmods):
                mod_append.append(colorama.Back.GREEN + mod.version_beatmods + colorama.Back.RESET)
            else:
                mod_append.append(colorama.Back.RED + mod.version_beatmods + colorama.Back.RESET)
        else:
            mod_append.append(colorama.Back.YELLOW + "Unknown" + colorama.Back.RESET)

        if not mod.version_github is None:
            if version.parse(mod.version_installed) >= version.parse(mod.version_github):
                mod_append.append(colorama.Back.GREEN + mod.version_github + colorama.Back.RESET)
            else:
                mod_append.append(colorama.Back.RED + mod.version_github + colorama.Back.RESET)
        else:
            mod_append.append(colorama.Back.YELLOW + "Unknown" + colorama.Back.RESET)

        tabulate_list.append(mod_append)

    # init colorama
    colorama.init()

    print(tabulate(tabulate_list, headers=["Filename", "Name", "GitHub URL", "File Version", "BeatMods Version", "GitHub Version"]))

    input("press enter to exit")
