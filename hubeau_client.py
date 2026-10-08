#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Client HTTP pour l'API Hub'Eau - Qualité de l'eau potable.
Documentation : https://hubeau.eaufrance.fr/page/api-qualite-eau-potable

Utilise exclusivement la bibliothèque standard Python (urllib.request, json)
pour garantir une compatibilité sans dépendances sur tout système Domoticz.
"""

import json
import logging
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

logger = logging.getLogger("HubEauClient")

API_BASE_URL = "https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable"
DEFAULT_USER_AGENT = "Domoticz-HubEau-Plugin/1.0 (+https://github.com/domoticz)"
DEFAULT_TIMEOUT = 30  # secondes


class HubEauError(Exception):
    """Exception levée en cas d'erreur de communication avec l'API Hub'Eau."""
    pass


class HubEauClient:
    """Client pour interroger les endpoints Hub'Eau Qualité de l'eau potable."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        timeout: int = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent

    def _get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Exécute une requête GET HTTP et parse la réponse JSON."""
        query_params = {k: v for k, v in (params or {}).items() if v is not None}
        query_str = urllib.parse.urlencode(query_params)
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if query_str:
            url = f"{url}?{query_str}"

        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "application/json",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                raw_data = response.read().decode(charset)
                return json.loads(raw_data)
        except urllib.error.HTTPError as err:
            raise HubEauError(f"Erreur HTTP {err.code} lors de l'appel {url}: {err.reason}") from err
        except (urllib.error.URLError, TimeoutError) as err:
            raise HubEauError(f"Délai d'attente ou erreur réseau lors de l'appel {url}: {err}") from err
        except json.JSONDecodeError as err:
            raise HubEauError(f"Réponse JSON invalide reçue de {url}: {err}") from err
        except Exception as err:
            raise HubEauError(f"Erreur inattendue lors de l'appel {url}: {err}") from err

    def get_communes_udi(
        self, code_commune: str, annee: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Récupère les réseaux de distribution (UDI) associés à une commune.
        
        :param code_commune: Code INSEE de la commune (ex: '45234')
        :param annee: Année optionnelle pour filtrer les réseaux
        :return: Liste de dictionnaires décrivant les UDI
        """
        params: Dict[str, Any] = {
            "code_commune": code_commune,
            "size": 50,
        }
        if annee is not None:
            params["annee"] = annee

        res = self._get("communes_udi", params)
        return res.get("data", [])

    def get_resultats_dis(
        self,
        code_commune: str,
        code_reseau: Optional[str] = None,
        size: int = 100,
        sort: str = "desc",
    ) -> List[Dict[str, Any]]:
        """
        Récupère les résultats des contrôles sanitaires (prélèvements et analyses) pour une commune.
        
        :param code_commune: Code INSEE de la commune
        :param code_reseau: Code du réseau / UDI (optionnel)
        :param size: Nombre maximal d'enregistrements (défaut: 100 pour couvrir l'ensemble des analyses récentes)
        :param sort: Ordre de tri par date_prelevement ('desc' par défaut pour avoir les plus récents en premier)
        :return: Liste des résultats d'analyses
        """
        params: Dict[str, Any] = {
            "code_commune": code_commune,
            "size": size,
            "sort": sort,
        }
        if code_reseau:
            params["code_reseau"] = code_reseau

        res = self._get("resultats_dis", params)
        return res.get("data", [])
