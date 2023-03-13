# BeatSaberModUpdates
This tool scans you Beat Saber plugins folder for mod updates using [BeatMods](https://beatmods.com) and the mods GitHub repository (if available).\
It searches for GitHub links in the mods details. This allows you to find updates for mods that are not availible in the Mod Assistant yet.\
It does not automatically update the mods, but it will list all the availible updates and GitHub links. Please always be careful when installing mods and updates.

## Do not forget to set the path to your BeatSaber installation in the config.json
If your Beat Saber installtion path is differnt from the default "C:/Program Files (x86)/Steam/steamapps/common/Beat Saber" you need to change the path in the config.json file. Otherwise the tool can not find and check your installed mods.

## GitHub API Token
You can also specify a GitHub API token in the config.json. GitHub limits the number of request to 60 requests per hour. The tool need one request per mod to check the version. So if you run the tool multiple times in a short time, you will most likely hit the limit very fast.
You can generate a new token under https://github.com/settings/tokens, it does not require any special permissions.
