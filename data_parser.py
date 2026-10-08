#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'extraction et de normalisation des données d'eau potable Hub'Eau.
Traite les données brutes issues des endpoints 'communes_udi' et 'resultats_dis'.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def format_date_french(raw_date: Optional[str]) -> str:
    """
    Formate une date ISO ou standard en affichage lisible français (JJ/MM/AAAA [HH:MM]).
    """
    if not raw_date:
        return ""
    raw = str(raw_date).strip()
    # Supprime 'Z' final si présent
    if raw.endswith("Z"):
        raw = raw[:-1]
    
    # Formats ISO possibles
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            pass
            
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(raw, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            pass

    return raw


# Définition des codes SANDRE des paramètres cibles
PARAM_NITRATES = "1340"         # Nitrates (en NO3)
PARAM_PH = "1302"               # Potentiel Hydrogène (pH)
PARAM_CONDUCTIVITE = "1303"     # Conductivité à 25°C
PARAM_DURETE = "7972"           # Titre hydrotimétrique (TH)
PARAM_CHLORE_LIBRE = "1398"     # Chlore libre
PARAM_CHLORE_TOTAL = "1399"     # Chlore total
PARAM_TEMPERATURE = "1301"      # Température de l'eau
PARAM_TURBIDITE = "1295"        # Turbidité néphélométrique NFU
PARAM_AMMONIUM = "1335"         # Ammonium (en NH4)


def parse_numeric_value(resultat_num: Any, resultat_alpha: Optional[str]) -> Optional[float]:
    """
    Extrait une valeur flottante fiable à partir des champs de résultat de l'API.
    
    :param resultat_num: Valeur du champ 'resultat_numerique'
    :param resultat_alpha: Valeur du champ 'resultat_alphanumerique'
    :return: Float ou None si non convertible
    """
    if resultat_num is not None:
        try:
            return round(float(resultat_num), 2)
        except (ValueError, TypeError):
            pass

    if resultat_alpha:
        clean = resultat_alpha.strip().replace(",", ".")
        # Supprime les préfixes de type '<', '>', '~'
        clean = re.sub(r"^[<>=~]\s*", "", clean)
        try:
            return round(float(clean), 2)
        except (ValueError, TypeError):
            pass

    return None


def extract_commune_udi_info(
    udi_list: List[Dict[str, Any]], code_reseau: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extrait les métadonnées de réseau et la date de dernière alimentation.
    
    :param udi_list: Liste des enregistrements UDI
    :param code_reseau: Code réseau spécifique demandé (optionnel)
    :return: Dictionnaire avec nom_commune, code_reseau, nom_reseau, debut_alim
    """
    if not udi_list:
        return {
            "nom_commune": "",
            "code_reseau": code_reseau or "",
            "nom_reseau": "",
            "debut_alim": "",
        }

    selected: Optional[Dict[str, Any]] = None

    if code_reseau:
        for udi in udi_list:
            if str(udi.get("code_reseau", "")).strip() == str(code_reseau).strip():
                selected = udi
                break

    if not selected:
        # Trie par année descendante si disponible, sinon prend le premier élément
        sorted_udi = sorted(
            udi_list,
            key=lambda x: str(x.get("annee", "")) or str(x.get("debut_alim", "")),
            reverse=True,
        )
        selected = sorted_udi[0]

    return {
        "nom_commune": selected.get("nom_commune", ""),
        "code_reseau": selected.get("code_reseau", ""),
        "nom_reseau": selected.get("nom_reseau", ""),
        "debut_alim": selected.get("debut_alim", "") or "",
    }


def parse_conformite(
    bact: Optional[str], pc: Optional[str], conclusion: Optional[str]
) -> Tuple[int, str]:
    """
    Détermine le statut d'alerte Domoticz et le libellé pour la conformité sanitaire.
    
    Niveaux d'alerte Domoticz :
    0 = Gris (Pas de statut / Inconnu)
    1 = Vert (Normal / Conforme)
    2 = Jaune (Attention / Dérogation)
    3 = Orange (Avertissement)
    4 = Rouge (Alarme / Non conforme)
    
    :return: Tuple (alert_level, status_text)
    """
    bact = (bact or "").strip().upper()
    pc = (pc or "").strip().upper()

    # Si l'un des contrôles est Non Conforme ('N')
    if bact == "N" or pc == "N":
        return 4, "Non conforme"

    # Si conforme avec dérogation ('D')
    if bact == "D" or pc == "D":
        return 2, "Dérogation"

    # Si conforme ('C')
    if bact == "C" or pc == "C":
        return 1, "Conforme"

    # Analyse textuelle de la conclusion sanitaire en repli
    if conclusion:
        conc_lower = conclusion.lower()
        if "non conforme" in conc_lower:
            return 4, "Non conforme"
        if "conforme" in conc_lower:
            return 1, "Conforme"

    return 0, "Inconnu"


def extract_water_quality_data(
    resultats: List[Dict[str, Any]], udi_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyse la liste des résultats d'analyses et synthétise les derniers paramètres mesurés.
    
    :param resultats: Liste d'analyses retournée par l'API resultats_dis
    :param udi_info: Informations UDI issues d'extract_commune_udi_info
    :return: Dictionnaire complet structuré pour les dispositifs Domoticz
    """
    data: Dict[str, Any] = {
        # Métadonnées
        "nom_commune": (udi_info or {}).get("nom_commune", ""),
        "code_reseau": (udi_info or {}).get("code_reseau", ""),
        "nom_reseau": (udi_info or {}).get("nom_reseau", ""),
        "debut_alim": (udi_info or {}).get("debut_alim", ""),
        # Dates et conformité
        "date_prelevement": None,
        "conformite_level": 0,
        "conformite_status": "Inconnu",
        "conclusion": "",
        # Paramètres cibles (valeur, valeur brute, unité, date de mesure)
        "nitrates": None,
        "ph": None,
        "conductivite": None,
        "durete": None,
        "chlore_libre": None,
        "temperature": None,
        # Paramètres complémentaires
        "chlore_total": None,
        "turbidite": None,
        "ammonium": None,
    }

    if not resultats:
        return data

    # La date du premier enregistrement (tri desc) correspond au prélèvement le plus récent
    first = resultats[0]
    data["date_prelevement"] = first.get("date_prelevement")
    data["date_prelevement_fr"] = format_date_french(data["date_prelevement"])
    data["debut_alim_fr"] = format_date_french(data["debut_alim"])
    data["conclusion"] = first.get("conclusion_conformite_prelevement") or ""
    
    if not data["nom_commune"]:
        data["nom_commune"] = first.get("nom_commune", "")

    # Calcul de la conformité du prélèvement le plus récent
    level, status = parse_conformite(
        first.get("conformite_limites_bact_prelevement"),
        first.get("conformite_limites_pc_prelevement"),
        data["conclusion"],
    )
    data["conformite_level"] = level
    data["conformite_status"] = status

    # Parcours des résultats pour trouver la mesure la plus récente pour chaque paramètre
    for row in resultats:
        code_param = str(row.get("code_parametre", "")).strip()
        libelle = (row.get("libelle_parametre") or "").lower()
        val_num = parse_numeric_value(row.get("resultat_numerique"), row.get("resultat_alphanumerique"))
        val_raw = row.get("resultat_alphanumerique") or str(val_num or "")
        unite = row.get("libelle_unite", "")
        date_mesure = row.get("date_prelevement", "")

        param_payload = {
            "value": val_num,
            "raw": val_raw,
            "unit": unite,
            "date": date_mesure,
        }

        # 1. Nitrates (1340)
        if data["nitrates"] is None and code_param == PARAM_NITRATES:
            data["nitrates"] = param_payload

        # 2. pH (1302)
        elif data["ph"] is None and (code_param == PARAM_PH or libelle == "ph"):
            data["ph"] = param_payload

        # 3. Conductivité (1303)
        elif data["conductivite"] is None and (code_param == PARAM_CONDUCTIVITE or "conductivit" in libelle):
            data["conductivite"] = param_payload

        # 4. Dureté de l'eau (7972 ou libellé hydrotimétrique)
        elif data["durete"] is None and (
            code_param == PARAM_DURETE or "hydrotim" in libelle or "duret" in libelle
        ):
            data["durete"] = param_payload

        # 5. Chlore libre (1398)
        elif data["chlore_libre"] is None and (
            code_param == PARAM_CHLORE_LIBRE or "chlore libre" in libelle
        ):
            data["chlore_libre"] = param_payload

        # 6. Température au prélèvement (1301)
        elif data["temperature"] is None and (
            code_param == PARAM_TEMPERATURE or "temp" in libelle
        ):
            data["temperature"] = param_payload

        # 7. Chlore total (1399)
        elif data["chlore_total"] is None and (
            code_param == PARAM_CHLORE_TOTAL or "chlore total" in libelle
        ):
            data["chlore_total"] = param_payload

        # 8. Turbidité (1295)
        elif data["turbidite"] is None and (
            code_param == PARAM_TURBIDITE or "turbidit" in libelle
        ):
            data["turbidite"] = param_payload

        # 9. Ammonium (1335)
        elif data["ammonium"] is None and (
            code_param == PARAM_AMMONIUM or "ammonium" in libelle
        ):
            data["ammonium"] = param_payload

    return data
