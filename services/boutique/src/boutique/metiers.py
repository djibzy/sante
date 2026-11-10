"""Métiers de la santé, pour ranger les tenues comme les soignants les cherchent."""

METIERS: dict[str, str] = {
    "infirmier": "Infirmiers et infirmières",
    "sage-femme": "Sages-femmes",
    "medecin": "Médecins",
    "pharmacie": "Pharmacie",
    "laboratoire": "Laboratoire",
    "dentiste": "Dentistes",
    "aide-soignant": "Aides-soignants",
    "etudiant": "Étudiants en santé",
}

GENRES: dict[str, str] = {"femme": "Femme", "homme": "Homme", "mixte": "Mixte"}
MANCHES: dict[str, str] = {"courtes": "Manches courtes", "longues": "Manches longues"}

# Grandes familles du menu : les tenues d'abord, puis le reste de nos services.
UNIVERS: dict[str, str] = {
    "tenues": "Tenues médicales",
    "equipement": "Kits et matériel",
    "campagnes": "Campagnes de sensibilisation",
}
