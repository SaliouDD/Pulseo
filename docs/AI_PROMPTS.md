# Gemini

Pulseo envoie à Gemini seulement le titre, l'extrait RSS et le nom de la source des nouveaux éléments sélectionnés. Le prompt est centralisé dans `backend/app/ai/prompts.py` et demande du JSON validé avant de composer le feed.

La langue système du téléphone est envoyée avec le feed. Gemini produit tous les champs éditoriaux dans cette langue, même si la source est dans une autre langue. Un cache distinct est conservé pour chaque langue.

Un rafraîchissement du cache traite le lot entier avec une seule requête Gemini. Le cache en mémoire est valable 15 minutes ; le feed n'appelle donc pas Gemini à chaque swipe.

Configuration locale : copiez `backend/.env.example` vers `backend/.env`, puis renseignez `GEMINI_API_KEY`. Ne versionnez jamais ce fichier.
