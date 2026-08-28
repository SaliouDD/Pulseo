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

## Démarrer l'application mobile

```bash
cd mobile
npm install
cp .env.example .env
npm start
```

Dans `.env`, utilisez l'adresse IP locale de votre ordinateur pour tester depuis Expo Go, par exemple `EXPO_PUBLIC_API_URL=http://192.168.1.20:8000`.

## État du MVP

Le squelette permet déjà à l'application mobile d'appeler `GET /health`. PostgreSQL, RSS et Gemini restent volontairement hors du premier jalon.
