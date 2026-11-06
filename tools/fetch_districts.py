"""OpenStreetMap'dan O'zbekiston tumanlari va shaharlarining HOZIRGI chegaralarini oladi.

  python tools/fetch_districts.py

Natija: data/uz_districts.geojson  (har bir tumanda: id, name — o'zbekcha lotin, region — viloyat ISO kodi)
Manba: © OpenStreetMap hissadorlari, ODbL 1.0 — video izohida avtomatik ko'rsatiladi.
"""
import json, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "uz_districts.geojson"
SERVERS = ["https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"]
HEADERS = {"User-Agent": "GeoIlmQuizBot/1.0 (educational quiz generator)"}
REGIONS = ["UZ-AN", "UZ-BU", "UZ-FA", "UZ-JI", "UZ-NG", "UZ-NW", "UZ-QA", "UZ-QR",
           "UZ-SA", "UZ-SI", "UZ-SU", "UZ-TK", "UZ-TO", "UZ-XO"]
CYR = re.compile(r"[А-Яа-яЁёЎўҚқҒғҲҳ]")


def overpass(query: str) -> dict:
    for k in range(6):
        url = SERVERS[k % len(SERVERS)]
        try:
            r = requests.post(url, data={"data": query}, headers=HEADERS, timeout=240)
            if r.status_code in (429, 504, 502, 503):
                print(f"  server band ({r.status_code}), kutamiz..."); time.sleep(20 * (k + 1)); continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  xato ({k + 1}/6): {e}"); time.sleep(10 * (k + 1))
    raise RuntimeError("Overpass javob bermadi")


def uz_name(tags: dict) -> str | None:
    for key in ("name:uz", "name:uz-Latn", "name"):
        n = tags.get(key)
        if n and not CYR.search(n):
            return n.replace("'", "‘").replace("`", "‘").replace("ʻ", "‘").replace("’", "‘")
    return tags.get("name:en")


def main():
    try:
        import osm2geojson
    except ImportError:
        sys.exit("Avval o'rnating:  pip install osm2geojson")
    feats = []
    for iso in REGIONS:
        print(f"{iso} ...")
        q = f"""[out:json][timeout:200];
        area["ISO3166-2"="{iso}"]["boundary"="administrative"]->.a;
        relation(area.a)["boundary"="administrative"]["admin_level"="6"];
        out geom;"""
        gj = osm2geojson.json2geojson(overpass(q))
        n = 0
        for f in gj["features"]:
            tags = (f.get("properties") or {}).get("tags", {})
            if f["geometry"]["type"] not in ("Polygon", "MultiPolygon"):
                continue
            name = uz_name(tags)
            if not name:
                continue
            feats.append({"type": "Feature",
                          "properties": {"id": f"OSM{f['properties'].get('id')}", "name": name, "region": iso,
                                         "name_en": tags.get("name:en", "")},
                          "geometry": f["geometry"]})
            n += 1
        print(f"  {n} ta tuman/shahar")
        time.sleep(3)
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    print(f"Tayyor: {OUT}  ({len(feats)} ta)")
    print("Nomlarni tekshirib chiqing: data/uz_districts.geojson ichidagi \"name\" maydonlari.")


if __name__ == "__main__":
    main()
