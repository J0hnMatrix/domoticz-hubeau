#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de résolution et validation de communes françaises.
Utilise l'API publique officielle geo.api.gouv.fr (Etalab / data.gouv.fr).
Permet aux utilisateurs de saisir :
- Un nom de ville (ex: 'Paris', 'Lyon', 'Orléans', 'Marseille')
- Un code postal (ex: '75001', '69001', '45000')
- Un code INSEE (ex: '75056', '69123', '45234')

Zéro dépendance tierce (urllib.request standard).
"""

import json
import logging
import re
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("CommuneResolver")

GEO_API_BASE_URL = "https://geo.api.gouv.fr"
DEFAULT_TIMEOUT = 10


class CommuneResolverError(Exception):
    """Exception en cas d'erreur de résolution de commune."""
    pass


class CommuneResolver:
    """Résolveur et validateur de commune via geo.api.gouv.fr."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.timeout = timeout

    def _query(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        query_str = urllib.parse.urlencode(params or {})
        url = f"{GEO_API_BASE_URL}/{endpoint.lstrip('/')}"
        if query_str:
            url = f"{url}?{query_str}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Domoticz-HubEau-Plugin/1.0 (+https://github.com/domoticz)",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                charset = resp.headers.get_content_charset() or "utf-8"
                return json.loads(resp.read().decode(charset))
        except urllib.error.HTTPError as err:
            if err.code == 404:
                return None
            raise CommuneResolverError(f"Erreur HTTP {err.code} sur {url}") from err
        except Exception as err:
            raise CommuneResolverError(f"Erreur lors de la requête vers {url}: {err}") from err

    def resolve(
        self, user_input: str
    ) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Optional[str]]:
        """
        Résout une saisie utilisateur en commune validée.

        :param user_input: Nom de ville, code postal ou code INSEE
        :return: Tuple (commune_selectionnee, alternatives, message_information)
        """
        clean_input = user_input.strip()
        if not clean_input:
            return None, [], "Aucune commune renseignée."

        # Cas 1 : Saisie de 5 chiffres (Code INSEE ou Code Postal)
        if re.match(r"^\d{5}$", clean_input) or re.match(r"^(2A|2B)\d{3}$", clean_input, re.I):
            # Test direct code INSEE
            try:
                res_insee = self._query(f"communes/{clean_input}")
                if res_insee and isinstance(res_insee, dict):
                    msg = (
                        f"Code INSEE '{clean_input}' validé : {res_insee.get('nom')} "
                        f"(Dép {res_insee.get('codeDepartement')}, CP {', '.join(res_insee.get('codesPostaux', []))})"
                    )
                    return res_insee, [], msg
            except Exception:
                pass

            # Si ce n'est pas un code INSEE direct, test comme code postal
            try:
                res_cp = self._query("communes", {"codePostal": clean_input})
                if res_cp and isinstance(res_cp, list) and len(res_cp) > 0:
                    # Tri par population descendante
                    res_cp.sort(key=lambda x: x.get("population", 0), reverse=True)
                    selected = res_cp[0]
                    alts = res_cp[1:]
                    msg = (
                        f"Code postal '{clean_input}' résolu vers {selected.get('nom')} "
                        f"(INSEE: {selected.get('code')}, Dép: {selected.get('codeDepartement')})"
                    )
                    if alts:
                        alts_str = ", ".join([f"{c.get('nom')} ({c.get('code')})" for c in alts[:3]])
                        msg += f" - Autres communes desservies par ce code postal : {alts_str}"
                    return selected, alts, msg
            except Exception:
                pass

            # Si l'API géo n'a pas répondu, repli sur le code brut
            return (
                {"code": clean_input, "nom": f"Commune {clean_input}"},
                [],
                f"Validation hors-ligne : utilisation du code '{clean_input}' comme code INSEE.",
            )

        # Cas 2 : Saisie textuelle (Nom de commune)
        try:
            results = self._query(
                "communes",
                {"nom": clean_input, "boost": "population", "limit": 5},
            )
            if results and isinstance(results, list) and len(results) > 0:
                selected = results[0]
                alts = results[1:]
                msg = (
                    f"Nom de ville '{clean_input}' résolu vers : {selected.get('nom')} "
                    f"(INSEE: {selected.get('code')}, Dép: {selected.get('codeDepartement')}, "
                    f"CP: {', '.join(selected.get('codesPostaux', []))})"
                )
                if alts:
                    alts_str = ", ".join(
                        [f"{c.get('nom')} (Dép {c.get('codeDepartement')}, INSEE {c.get('code')})" for c in alts[:3]]
                    )
                    msg += f" - Autres homonymes trouvés : {alts_str}"
                return selected, alts, msg
            else:
                return (
                    None,
                    [],
                    f"Aucune commune française trouvée correspondant au nom '{clean_input}'.",
                )
        except Exception as err:
            return (
                None,
                [],
                f"Impossible de joindre l'API de résolution géographique : {err}",
            )
