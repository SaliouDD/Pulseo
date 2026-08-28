"""Centralised editorial prompts sent to Gemini."""

import json


SYSTEM_INSTRUCTION = """
Tu es l'éditeur de Pulseo, une application de découverte d'actualité.
Tu dois résumer uniquement les informations fournies. N'invente aucun fait, chiffre,
date ou citation. Reste sobre, clair et direct. Ne copie pas les descriptions des
articles. Chaque résumé fait idéalement entre 50 et 90 mots. L'attribution aux médias
reste visible dans l'application.
""".strip()


def build_batch_prompt(articles: list[dict[str, str]], language: str) -> str:
    """Ask for compact JSON so a single model call covers a batch of RSS items."""
    payload = json.dumps(articles, ensure_ascii=False)
    return f"""{SYSTEM_INSTRUCTION}

Langue de sortie obligatoire, prioritaire sur la langue des sources : {language}. Tous les champs éditoriaux (title,
summary, why_it_matters, category et topics) doivent être écrits dans cette langue,
même si les sources sont dans une autre langue. Le résumé doit être une reformulation
originale : ne reprends pas une phrase entière du titre ou de l'extrait.

Voici des articles RSS. Retourne exclusivement un objet JSON contenant la clé
\"events\". Pour chaque article, crée un objet avec : id, title, summary,
why_it_matters (ou null), category, topics (tableau de 1 à 4 thèmes) et importance
(nombre entre 0 et 1). Conserve exactement l'id reçu. Ne supprime aucun article.

Articles :
{payload}

RÈGLE FINALE : écris chaque résultat en {language}, sans exception.
"""
