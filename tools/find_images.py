"""List Blooncyclopedia image names matching a regex, to find icon file names for fetch_icons.py.

Usage: python3 -I tools/find_images.py 'Easy|Medium|Hard'      (scans every BTD6_* file name)
"""
import json
import re
import sys
import time
import urllib.parse
import urllib.request

API = "https://www.bloonswiki.com/api.php"
UA = "btd6-tech-wiki/0.1 (personal static site build script)"


def main():
    pattern = re.compile(sys.argv[1], re.I)
    cont = {}
    while True:
        q = {"action": "query", "list": "allimages", "aiprefix": "BTD6_", "ailimit": "500", "format": "json", **cont}
        req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.loads(r.read())
        for i in d["query"]["allimages"]:
            if pattern.search(i["name"]):
                print(i["name"])
        if "continue" not in d:
            return
        cont = {"aicontinue": d["continue"]["aicontinue"]}
        time.sleep(0.4)


if __name__ == "__main__":
    main()
