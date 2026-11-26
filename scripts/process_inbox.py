#!/usr/bin/env python3
"""Traite les photos déposées dans inbox/ (originaux avec GPS).

- Chaque photo est associée au traiteur le plus proche (GPS EXIF), si le match est sûr.
- Plusieurs photos du même lieu : la plus ancienne = photo principale, la suivante = photo secrète.
  Un fichier dont le nom contient « secret » est toujours la photo secrète.
- Les photos traitées sont supprimées de inbox/ ; les ambiguës (pas de GPS, deux traiteurs proches)
  restent dans inbox/ et sont listées dans inbox/A_VERIFIER.txt.
Code de sortie 0 ; imprime « CHANGED » si au moins une visite a été ajoutée.
"""
import glob, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import add_photo as ap  # noqa: E402

INBOX = os.path.join(ROOT, "inbox")
EXT = (".jpg", ".jpeg", ".heic", ".heif", ".png", ".webp")


def exif_dt(img):
    ex = img.getexif()
    return str(ex.get_ifd(0x8769).get(0x9003) or ex.get(0x0132) or "")


def main():
    files = sorted(f for f in glob.glob(os.path.join(INBOX, "*")) if f.lower().endswith(EXT))
    P = json.load(open(ap.PLACES, encoding="utf-8"))["places"]
    groups, bad = {}, []
    for f in files:
        img = ap.open_img(f)
        lat, lng, _ = ap.exif_info(img)
        if lat is None:
            bad.append((f, "pas de GPS"))
            continue
        c = sorted(((ap.dist_m(lat, lng, p["lat"], p["lng"]), p) for p in P), key=lambda t: t[0])[:2]
        sure = c[0][0] <= ap.SURE_M and c[1][0] >= ap.RATIO * max(c[0][0], 5)
        if not sure:
            bad.append((f, "ambigu : " + " / ".join(f"{p['name']} ({d:.0f} m, id {p['id']})" for d, p in c)))
            continue
        groups.setdefault(c[0][1]["id"], []).append((exif_dt(img), f))

    changed = False
    for pid, lst in groups.items():
        lst.sort()
        sec = [f for _, f in lst if "secret" in os.path.basename(f).lower()]
        rest = [f for _, f in lst if f not in sec]
        front = rest[0] if rest else sec.pop(0)
        back = (sec + rest[1:])[:1]
        r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "add_photo.py"), front, *back, "--id", str(pid)],
                           capture_output=True, text=True)
        print(r.stdout.strip())
        if r.returncode == 0:
            changed = True
            for _, f in lst:
                os.remove(f)
        else:
            bad += [(f, "erreur : " + r.stderr.strip()[-200:]) for _, f in lst]

    note = os.path.join(INBOX, "A_VERIFIER.txt")
    if bad:
        with open(note, "w", encoding="utf-8") as fh:
            fh.write("Photos non placées (demander à Claude ou relancer add_photo.py --id N) :\n")
            for f, why in bad:
                fh.write(f"- {os.path.basename(f)} : {why}\n")
        print(open(note, encoding="utf-8").read())
    elif os.path.exists(note):
        os.remove(note)
    if changed:
        print("CHANGED")


if __name__ == "__main__":
    main()
