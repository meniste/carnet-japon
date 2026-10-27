# Carnet du Japon — version publique (GitHub Pages)

Site en lecture seule du carnet de voyage de Baptiste (Japon, 27 oct. – 15 nov. 2026), pour sa famille, sans compte.
Publié par GitHub Pages depuis `main` / racine : https://meniste.github.io/carnet-japon/

## D'où viennent les données
Baptiste écrit ses jours et ajoute ses photos dans l'artifact claude.ai « Carnet du Japon » :
https://claude.ai/artifact/WvSynLUJBi3ZcVcA8epopd
- Textes : base de données de l'artifact, collection `days` (un document par jour, id = date `AAAA-MM-JJ`).
- Photos : assets de l'artifact ; chaque jour liste `photos: [{id, w, h}]`.

## Mettre à jour le site (« mets à jour le carnet »)
1. Exporter les jours : outil ArtifactData, action `list`, url de l'artifact, collection `days`, `out_dir` = un dossier de travail (ex. `export`).
2. Récupérer chaque photo citée qui manque dans `photos/` : outil Artifact, action `read`, url de l'artifact, `path` = id de l'asset. Copier le fichier obtenu en `photos/<id>.jpg`.
3. Lancer `CARNET_MDP=<mot de passe> python3 build.py <carnet.html> export/days <dossier_photos> .`
   - Le mot de passe n'est jamais écrit dans le dépôt (public) : le demander à Baptiste s'il n'est pas connu.
   - `<carnet.html>` : la page de l'artifact (Artifact action `read`, fichier sauvegardé) **sans** le squelette `<!doctype>…<body>` ajouté par claude.ai : garder seulement ce qui est entre `<body>` et `</body>`.
   - Le script rechiffre toujours la page et `data.bin`, et chiffre seulement les photos absentes de `photos/`.
4. Commit sur `main` avec un message du type « Carnet : jours du 27 au 29 oct. ».

## Mot de passe
Le site est chiffré (AES-256-GCM, clé dérivée du mot de passe en minuscules par PBKDF2 avec `sel.txt`).
- `index.html` : écran de mot de passe (saisie visible) + la page de l'artifact chiffrée. La clé est gardée dans
  l'IndexedDB de l'appareil : on ne la saisit qu'une fois par appareil.
- `sw.js` : service worker qui répond aux requêtes `data.json` et `photos/<id>.jpg` de la page en déchiffrant
  `data.bin` et `photos/<id>.bin`.
- Ne jamais changer `sel.txt` ni le mot de passe sans le vouloir : tous les appareils devraient le ressaisir, et
  toutes les photos `.bin` devraient être rechiffrées (les supprimer avant le build, en fournissant les photos en clair).
- Ne jamais publier de texte ni de photo en clair dans le dépôt.

## Fichiers
- `index.html` : écran de mot de passe ; la page déchiffrée est la même que l'artifact et, hors de claude.ai, charge `data.json` en lecture seule.
- `data.bin` : `{"days": [{date, place, placeJp, region, lat, lng, title, text, photos:[{id,w,h}]}]}`, chiffré.
- `photos/<id>.bin` : photos JPEG chiffrées (déjà réduites à 2048 px par l'artifact).
- `sw.js`, `sel.txt` : voir « Mot de passe ».
- `apple-touch-icon.png` (180 px, écran d'accueil iPhone, nom « Japon ») et `favicon.png` : icône soleil, Fuji et torii.
- `robots.txt` + balise `noindex` : site hors des moteurs de recherche.
- `build.py` : construit le site à partir d'un export.
