#!/usr/bin/env python3
"""Ajoute une visite (1 ou 2 photos) à la carte « Les traiteurs chinois ».

Usage :
  python3 scripts/add_photo.py FRONT.jpg [BACK.jpg] [--id N] [--date AAAA-MM-JJ] [--dry-run]

- FRONT = photo principale (carte), BACK = photo secrète (optionnelle, coin plié).
- Sans --id : lit le GPS EXIF de FRONT (ou de BACK) et cherche le traiteur le plus proche.
  * match sûr (≤ 60 m et 2e candidat ≥ 1,8× plus loin)  -> continue
  * sinon -> affiche les candidats et sort avec le code 2 (relancer avec --id N)
- Date : DateTimeOriginal EXIF, sinon aujourd'hui (ou --date).
- Écrit photos/<id>/front.webp (et back.webp), sans métadonnées, 2400 px max.
- Met à jour data/visits.json (remplace la visite existante du même id).
Sortie finale : une ligne JSON « RESULT {...} » lisible par Claude.
"""
import argparse, datetime as dt, json, math, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLACES = os.path.join(ROOT, "data", "places.json")
VISITS = os.path.join(ROOT, "data", "visits.json")
MAXPX, QUALITY = 2400, 90
SURE_M, RATIO, SHOW_M = 60, 1.8, 250

try:
    from PIL import Image, ImageOps
except ImportError:
    sys.exit("Pillow manquant : pip install -r scripts/requirements.txt")
try:
    import pillow_heif  # HEIC/HEIF (iPhone)
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None


def open_img(path):
    if path.lower().endswith((".heic", ".heif")) and pillow_heif is None:
        sys.exit("Fichier HEIC : installer pillow-heif (pip install -r scripts/requirements.txt)")
    return Image.open(path)


def exif_info(img):
    """-> (lat, lng | None, date 'AAAA-MM-JJ' | None)"""
    ex = img.getexif()
    date = None
    sub = ex.get_ifd(0x8769)  # Exif IFD
    raw = sub.get(0x9003) or ex.get(0x0132)  # DateTimeOriginal / DateTime
    if raw:
        try:
            date = dt.datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S").date().isoformat()
        except ValueError:
            pass
    gps = ex.get_ifd(0x8825)
    lat = lng = None
    if gps and 2 in gps and 4 in gps:
        def dec(v, ref):
            d, m, s = (float(x) for x in v)
            x = d + m / 60 + s / 3600
            return -x if ref in ("S", "W") else x
        lat = dec(gps[2], gps.get(1, "N"))
        lng = dec(gps[4], gps.get(3, "E"))
    return lat, lng, date


def dist_m(a, b, c, d):
    R = 6371000
    p1, p2 = math.radians(a), math.radians(c)
    dp, dl = p2 - p1, math.radians(d - b)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def save_webp(src, dst):
    img = ImageOps.exif_transpose(open_img(src)).convert("RGB")
    img.thumbnail((MAXPX, MAXPX), Image.LANCZOS)
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    img.save(dst, "WEBP", quality=QUALITY, method=6)  # no exif -> GPS stripped
    return img.size


def save_thumb(front):
    """Small copy used on the map (cards are ~112 css px); the full image loads only when a card is opened."""
    img = Image.open(front).convert("RGB")
    img.thumbnail((420, 420), Image.LANCZOS)
    img.save(front.replace("front.webp", "thumb.webp"), "WEBP", quality=80, method=6)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("photos", nargs="+", help="FRONT [BACK]")
    ap.add_argument("--id", type=int)
    ap.add_argument("--date")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if len(a.photos) > 2:
        sys.exit("Maximum 2 photos : FRONT [BACK]")
    P = json.load(open(PLACES, encoding="utf-8"))
    places = {p["id"]: p for p in P["places"]}

    lat = lng = date = None
    for ph in a.photos:
        la, ln, de = exif_info(open_img(ph))
        if lat is None and la is not None:
            lat, lng = la, ln
        date = date or de
    date = a.date or date or dt.date.today().isoformat()

    cands = []
    if lat is not None:
        cands = sorted(((dist_m(lat, lng, p["lat"], p["lng"]), p) for p in P["places"]), key=lambda t: t[0])[:5]
        print(f"GPS {lat:.6f},{lng:.6f}")
        for d, p in cands:
            if d <= SHOW_M:
                print(f"  {d:6.0f} m  id={p['id']:<4} {p['name']}  —  {p['address']}")
    else:
        print("Pas de GPS dans les photos.")

    if a.id is not None:
        if a.id not in places:
            sys.exit(f"id {a.id} inconnu")
        pid = a.id
    else:
        sure = cands and cands[0][0] <= SURE_M and (len(cands) < 2 or cands[1][0] >= RATIO * max(cands[0][0], 5))
        if not sure:
            print("AMBIGU : relancer avec --id N (vérifier l'enseigne sur la photo).")
            sys.exit(2)
        pid = cands[0][1]["id"]

    p = places[pid]
    rel = lambda n: f"photos/{pid}/{n}.webp"
    res = {"id": pid, "name": p["name"], "address": p["address"], "date": date,
           "front": rel("front"), "back": rel("back") if len(a.photos) == 2 else None,
           "gps_m": round(cands[0][0]) if cands else None, "dry_run": a.dry_run}
    if not a.dry_run:
        save_webp(a.photos[0], os.path.join(ROOT, res["front"]))
        save_thumb(os.path.join(ROOT, res["front"]))
        backf = os.path.join(ROOT, rel("back"))
        if len(a.photos) == 2:
            save_webp(a.photos[1], backf)
        elif os.path.exists(backf):
            os.remove(backf)
        V = json.load(open(VISITS, encoding="utf-8"))
        vs = [v for v in V.get("visits", []) if v["id"] != pid]
        v = {"id": pid, "date": date, "front": res["front"]}
        if res["back"]:
            v["back"] = res["back"]
        vs.append(v)
        vs.sort(key=lambda v: (v["date"], v["id"]))
        V["visits"] = vs
        with open(VISITS, "w", encoding="utf-8") as f:
            json.dump(V, f, ensure_ascii=False, indent=1)
            f.write("\n")
    print("RESULT " + json.dumps(res, ensure_ascii=False))


if __name__ == "__main__":
    main()
