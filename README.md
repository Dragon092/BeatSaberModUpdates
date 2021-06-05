# BeatSaberModUpdates
This tool scans you BeatSaber plugins folder for mod updates using [BeatMods](https://beatmods.com) and the mods GitHub repository (if available).

## Pre-Releases
You can find the latest pre-release version under [Actions](https://github.com/Dragon092/BeatSaberTool/actions/workflows/main.yml).

Just download the artifact under the latest successful build.

**Do not forget to set the path to your BeatSaber installation in the config.json.**

You can also specify a GitHub API token there. GitHub limits the number of request to 60 requests per hour. The tool need one request per mod to check the version. So if you run the tool multiple times in a short time, you will most likely hit the limit very fast.
You can generate a new token under https://github.com/settings/tokens, it does not require any special permissions.