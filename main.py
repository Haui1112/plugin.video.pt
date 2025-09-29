import os
import sys
from datetime import datetime, timedelta
import requests
import json
import xbmcvfs
from urllib.parse import urlencode, parse_qsl

import xbmcgui
import xbmcplugin
from xbmcaddon import Addon
from xbmcvfs import translatePath

URL = sys.argv[0]
HANDLE = int(sys.argv[1])
ADDON_PATH = translatePath(Addon().getAddonInfo("path"))
IMAGE_DIR = os.path.join(ADDON_PATH, "resources", "images")
ADDON_ID = "plugin.video.pt"
USERDATA_PATH = f"special://userdata/addon_data/{ADDON_ID}/"
FAVORITE = os.path.join(USERDATA_PATH, "favorite.json")

xbmc.log(f"ADDON_PATH {ADDON_PATH}", xbmc.LOGINFO)


def get_url(**kwargs):
    return "{}?{}".format(URL, urlencode(kwargs))


def fetch_instances(filepath):
    """Real instance fetching"""
    request = requests.get(
        "https://instances.joinpeertube.org/api/v1/instances/hosts?count=1000&start=0&sort=createdAt"
    )
    r = request.json()
    r["date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        with xbmcvfs.File(filepath, "w") as instances_file:
            instances_file.write(json.dumps(r, ensure_ascii=False, indent=4))
    except:
        xbmc.log("Could not write %s" % filepath, xbmc.LOGDEBUG)
    return r


def get_instances():
    filename = "instances.json"
    if not xbmcvfs.exists(USERDATA_PATH):
        try:
            xbmcvfs.mkdir(USERDATA_PATH)
        except:
            xbmc.log("Could not write %s" % USERDATA_PATH, xbmc.LOGDEBUG)
    FILE_PATH = os.path.join(USERDATA_PATH, filename)
    if not xbmcvfs.exists(FILE_PATH):
        xbmc.log("No file, requesting new data!", xbmc.LOGDEBUG)
        r = fetch_instances(FILE_PATH)
    else:
        with xbmcvfs.File(FILE_PATH) as instances_file:
            r = json.load(instances_file)
        t1 = datetime.strptime(r["date"], "%Y-%m-%d %H:%M")
        t2 = datetime.now()
        if t2 - t1 > timedelta(days=1):
            r = fetch_instances(FILE_PATH)
    return r["data"]


def list_instances():
    xbmcplugin.setPluginCategory(HANDLE, "Peertube Servers")
    xbmcplugin.setContent(HANDLE, "movies")
    instances = get_instances()
    for index, genre_info in enumerate(instances):
        list_item = xbmcgui.ListItem(label=genre_info["host"])
        info_tag = list_item.getVideoInfoTag()
        info_tag.setMediaType("video")
        info_tag.setTitle(genre_info["host"])
        info_tag.setGenres([genre_info["host"]])
        url = get_url(action="listing", host=genre_info["host"])
        is_folder = True
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.endOfDirectory(HANDLE)


def get_videos(host):
    request = requests.get("https://%s/api/v1/videos?isLocal=true" % (host))
    r = request.json()
    return r["data"]


def generate_item_info(
    self,
    name,
    url,
    is_folder=True,
    thumbnail="",
    aired="",
    duration=0,
    plot="",
):
    return {
        "name": name,
        "url": url,
        "is_folder": is_folder,
        "art": {
            "thumb": thumbnail,
        },
        "info": {"aired": aired, "duration": duration, "plot": plot, "title": name},
    }


def list_videos(host):
    data = {}
    if xbmcvfs.exists(FAVORITE):
        with xbmcvfs.File(FAVORITE, "r") as favorite:
            try:
                data = json.load(favorite)
            except:
                data = {}
    if host not in data:
        data[host] = "TODO"
    try:
        with xbmcvfs.File(FAVORITE, "w") as favorite:
            favorite.write(json.dumps(data, ensure_ascii=False, indent=4))
    except:
        xbmc.log("Could not write %s" % FAVORITE, xbmc.LOGDEBUG)
    genre_info = get_videos(host)
    xbmcplugin.setPluginCategory(HANDLE, "Videos")
    xbmcplugin.setContent(HANDLE, "movies")
    videos = genre_info
    for video in videos:
        list_item = xbmcgui.ListItem(label=video["name"])
        info_tag = list_item.getVideoInfoTag()
        info_tag.setMediaType("movie")
        info_tag.setTitle(video["name"])
        list_item.setProperty("IsPlayable", "true")
        url = get_url(action="play", video=get_video(host, video["id"]))
        is_folder = False
        xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_LABEL_IGNORE_THE)
    xbmcplugin.addSortMethod(HANDLE, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.endOfDirectory(HANDLE)


def get_video(host, id):
    xbmc.log("host is %s" % host, xbmc.LOGDEBUG)
    xbmc.log("id is %s" % id, xbmc.LOGDEBUG)
    request = requests.get("https://%s/api/v1/videos/%d" % (host, id))
    r = request.json()
    xbmc.log("request is %s" % r, xbmc.LOGDEBUG)
    return r["streamingPlaylists"][0]["playlistUrl"]


def play_video(path):
    play_item = xbmcgui.ListItem(offscreen=True)
    play_item.setPath(path)
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def delete_instance(host):
    xbmc.log("Delete %s" % host, xbmc.LOGINFO)
    with xbmcvfs.File(FAVORITE, "r") as favorite:
        try:
            data = json.load(favorite)
        except Exception as e:
            xbmc.log(f"Could not read {FAVORITE} beacause {e}", xbmc.LOGDEBUG)
            data = {}
    if host in data:
        data.pop(host)
    try:
        with xbmcvfs.File(FAVORITE, "w") as favorite:
            favorite.write(json.dumps(data, ensure_ascii=False, indent=4))
    except Exception as e:
        xbmc.log(f"Could not write {FAVORITE} because {e}", xbmc.LOGDEBUG)


def home():
    xbmcplugin.setPluginCategory(HANDLE, "Peertube")
    xbmcplugin.setContent(HANDLE, "movies")

    url = get_url(action="instances")
    list_item = xbmcgui.ListItem("Instances from joinpeertube.org")
    list_item.setArt({"icon": f"{IMAGE_DIR}/icon.png"})
    list_item.setInfo("video", {"plot": "Find instance on joinpeertube.org"})
    is_folder = True
    xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

    if xbmcvfs.exists(FAVORITE):
        with xbmcvfs.File(FAVORITE, "r") as favorite:
            try:
                data = json.load(favorite)
            except:
                data = {}
            for instance in data:
                list_item = xbmcgui.ListItem(instance)
                list_item.setArt({"icon": "icon.png"})
                url_delete = get_url(action="delete", host=instance)
                list_item.addContextMenuItems(
                    [("Delete", f"Container.Update({url_delete})")]
                )
                is_folder = True
                url = get_url(action="listing", host=instance)
                xbmcplugin.addDirectoryItem(HANDLE, url, list_item, is_folder)

    xbmcplugin.endOfDirectory(HANDLE)


def router(paramstring):
    params = dict(parse_qsl(paramstring))
    if not params:
        home()
    elif params["action"] == "instances":
        list_instances()

    elif params["action"] == "delete":
        delete_instance(params["host"])
        home()

    elif params["action"] == "listing":
        list_videos(params["host"])

    elif params["action"] == "play":
        play_video(params["video"])
    else:
        raise ValueError(f"Invalid paramstring: {paramstring}!")


if __name__ == "__main__":
    router(sys.argv[2][1:])
