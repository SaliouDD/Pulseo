# Pulseo

MVP de découverte d'actualité : une application Expo et une API FastAPI séparées.

## Démarrer le backend

```bash
cd backend
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Vérifier ensuite `http://localhost:8000/health`.

Le premier appel à `http://localhost:8000/feed` collecte quelques flux RSS et génère un lot de résumés Gemini. Configurez auparavant `backend/.env` en copiant `backend/.env.example` et en ajoutant votre clé Gemini. Le résultat est gardé 15 minutes en mémoire pour limiter les appels IA.

## Démarrer l'application mobile

```bash
cd mobile
npm install
cp .env.example .env
npm start
```

Dans `.env`, utilisez l'adresse IP locale de votre ordinateur pour tester depuis Expo Go, par exemple `EXPO_PUBLIC_API_URL=http://192.168.1.20:8000`.

## État du MVP

L'application mobile affiche un feed vertical de premières actualités réelles via `GET /feed`. PostgreSQL et le stockage persistant sont les prochaines étapes ; le premier feed est volontairement conservé en mémoire.
