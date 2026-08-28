# Base de données Supabase

Le projet Supabase de Pulseo est `mazvgwomwqfkeesyhmyr`.

Le schéma initial est versionné dans `supabase/migrations/202608280001_initial_pulseo_schema.sql`. Il crée `sources`, `articles`, `events`, `event_summaries`, `event_sources` et `interactions`.

`event_summaries` contient une seule variante par couple **événement + langue**. Tous les utilisateurs réglés dans une même langue lisent donc la même variante persistée, sans nouvel appel Gemini individuel.

Le backend FastAPI se connecte directement à PostgreSQL. L'application mobile ne reçoit jamais l'URL de base de données, la clé Gemini ou une clé Supabase sensible.

Dans Supabase, ouvrez **Connect → Session pooler**, puis placez l'URL PostgreSQL dans `backend/.env` :

```dotenv
DATABASE_URL=postgresql://postgres.<project-ref>:<mot-de-passe>@<pooler>:5432/postgres
```

Ne versionnez jamais cette URL avec son mot de passe.
