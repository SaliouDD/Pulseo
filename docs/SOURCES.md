# Sources initiales

Le premier feed utilise deux flux RSS publics, configurés dans `backend/app/services/feed.py` :

- France 24 (français) : `https://www.france24.com/fr/rss`
- BBC News World (anglais) : `https://feeds.bbci.co.uk/news/world/rss.xml`

Chaque élément conserve le média et le lien vers l'article original. Une source indisponible est ignorée sans interrompre la collecte des autres flux.
