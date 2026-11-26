# Les traiteurs chinois — carte-hommage

Site statique (Vercel) : une carte de Paris au trait d'encre sur papier, où chaque traiteur chinois
photographié par Javier apparaît comme une petite photo instantanée accrochée à son point.
Titre : « Les traiteurs chinois » / sous-titre « nourrissant N histoires » (N = nombre de visites).
Langue du site : français. Javier écrit en espagnol : réponds-lui en espagnol.

## Structure
- `index.html` — tout le site (HTML + CSS + JS, aucun build). Charge les données ci-dessous.
- `data/places.json` — 304 traiteurs : `id, label, name, address, arr, lat, lng, gmaps, r` (r = inclinaison de la carte en °)
  + `map` (projection : x=(lng-lng0)*mx*PX+ox, y=(lat0-lat)*my*PX+oy) + `demo` (ids pour `?demo`).
- `data/visits.json` — visites : `{id, date, front, back?}`. C'est la seule source de « ce qui est photographié ».
- `photos/<id>/front.webp` (+ `back.webp` = photo secrète) — 2400 px max, qualité 90, sans EXIF.
- `streets.json` (rues dans le périphérique, delta-encodées, en décimètres) et `water.png` (Seine + canaux, données officielles « Plan de voirie – Voies d'eau »).
- `scripts/add_photo.py` — ajoute une visite.

## Ajouter une photo (tâche la plus fréquente)
Javier envoie 1 ou 2 photos et dit « añade esto ».
1. Sauve les pièces jointes dans `/tmp`, puis : `python3 scripts/add_photo.py /tmp/A.jpg [/tmp/B.jpg]`
   - 1ʳᵉ photo = principale, 2ᵉ (optionnelle) = photo secrète → la carte aura le coin plié.
   - Si Javier dit laquelle est la secrète, respecte-le (l'ordre des arguments décide).
2. Le script lit le GPS EXIF et choisit le traiteur le plus proche.
   - Regarde toujours la photo : l'enseigne doit correspondre au nom trouvé.
   - Code de sortie 2 (ambigu / pas de GPS) ou enseigne différente → choisis avec l'enseigne et la liste des candidats,
     relance avec `--id N`. Si tu doutes encore, demande à Javier avant d'écrire.
   - Traiteur absent de `places.json` → demande confirmation, ajoute-le (id = max+1, label du type `40b`, r aléatoire entre -2.6 et 2.6), puis relance.
3. Vérifie `data/visits.json`, commit (`Ajoute <nom>`), push sur `main` → Vercel publie seul (~1 min).
4. Réponds en une ligne : nom, adresse, date, avec ou sans photo secrète.
Pas de GPS (photo partagée depuis iPhone sans localisation) : utilise l'enseigne, et rappelle-lui « Options → Inclure la localisation ».
HEIC : nécessite `pip install -r scripts/requirements.txt` (pillow-heif).

## Inbox (originaux avec GPS)
Javier peut déposer les originaux dans `inbox/` (Safari → github.com → Add file → Upload files → Parcourir/Fichiers).
L'action GitHub `.github/workflows/inbox.yml` lance `scripts/process_inbox.py` : match GPS sûr → visite ajoutée et fichier supprimé ;
sinon le fichier reste et est listé dans `inbox/A_VERIFIER.txt`. Si Javier demande « revisa la bandeja », traite ces cas
à la main (`add_photo.py inbox/X --id N`, en lisant l'enseigne), puis supprime les fichiers traités.
Les pièces jointes du chat Claude arrivent sans EXIF (pas de GPS ni date) : identifier par l'enseigne.

## Règles de design (validées par Javier — ne pas changer sans demande)
- Papier crème avec grain/fibres/taches **solidaires de la carte** (bougent et zooment avec elle) ; seul le léger vignettage est fixe à l'écran. La feuille ne montre jamais de bord (zoom/pan bornés).
- Encre brun-noir chaud, trait avec grain ; l'eau en bleu-gris aquarelle, avec grain aussi.
- Seuls les lieux photographiés ont une carte ; les autres = points d'encre très discrets, non cliquables.
- Carte : papier blanc chaud, ombres en couches. Photos affichées telles quelles (aucun filtre, vignette ni grain). Ne pas écrire « polaroid » dans l'interface.
- Coin supérieur droit plié **uniquement** si photo secrète. Clic sur le coin → rotation 3D, le dos montre la photo secrète, **sans légende**, coin plié côté gauche.
- Clic sur une carte → zoom vers le centre, fond assombri en sépia (pas noir), transition douce ; clic sur la carte → retour exact à sa place.
- Pas de boutons de contrôle visibles. Polices : Cormorant Garamond (tout), Syne (sous-titre, majuscules espacées).

## Développement
Servir en local : `python3 -m http.server` (le fetch ne marche pas en file://). `?demo` affiche des cartes d'exemple si `visits.json` est vide.
