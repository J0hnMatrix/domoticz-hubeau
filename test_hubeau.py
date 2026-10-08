#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Suite de tests unitaires pour le plugin Domoticz Hub'Eau.
Testable avec unittest standard : python -m unittest test_hubeau.py
"""

import unittest
from unittest.mock import MagicMock, patch

from data_parser import (
    extract_commune_udi_info,
    extract_water_quality_data,
    format_date_french,
    parse_conformite,
    parse_numeric_value,
)
from hubeau_client import HubEauClient, HubEauError
from plugin import (
    UNIT_CHLORE_LIBRE,
    UNIT_CHLORE_TOTAL,
    UNIT_CONCLUSION,
    UNIT_CONDUCTIVITE,
    UNIT_CONFORMITE,
    UNIT_DATE_ALIM,
    UNIT_DATE_PRELEVEMENT,
    UNIT_DURETE,
    UNIT_NITRATES,
    UNIT_PH,
    UNIT_TEMPERATURE,
    UNIT_TURBIDITE,
    HubEauPlugin,
    MockDevice,
)


class TestDataParser(unittest.TestCase):
    """Tests unitaires du parseur de données Hub'Eau."""

    def test_parse_numeric_value_clean_floats(self):
        self.assertEqual(parse_numeric_value(12.34, "12,34"), 12.34)
        self.assertEqual(parse_numeric_value(0, "0"), 0.0)
        self.assertEqual(parse_numeric_value(7.6, "7,6"), 7.6)

    def test_parse_numeric_value_french_comma_and_prefixes(self):
        self.assertEqual(parse_numeric_value(None, "14,52"), 14.52)
        self.assertEqual(parse_numeric_value(None, "<0,01"), 0.01)
        self.assertEqual(parse_numeric_value(None, "< 10"), 10.0)
        self.assertEqual(parse_numeric_value(None, "traces"), None)
        self.assertEqual(parse_numeric_value(None, None), None)

    def test_format_date_french(self):
        self.assertEqual(format_date_french("2026-07-30T12:35:00Z"), "30/07/2026 12:35")
        self.assertEqual(format_date_french("2026-07-30 12:35:00"), "30/07/2026 12:35")
        self.assertEqual(format_date_french("2020-01-01"), "01/01/2020")
        self.assertEqual(format_date_french("30/07/2026 12:35:00"), "30/07/2026 12:35")
        self.assertEqual(format_date_french(""), "")
        self.assertEqual(format_date_french(None), "")

    def test_parse_conformite(self):
        # Conforme
        level, status = parse_conformite("C", "C", "Eau conforme")
        self.assertEqual(level, 1)
        self.assertEqual(status, "Conforme")

        # Non conforme
        level, status = parse_conformite("N", "C", "Eau non conforme")
        self.assertEqual(level, 4)
        self.assertEqual(status, "Non conforme")

        # Dérogation
        level, status = parse_conformite("D", "C", "")
        self.assertEqual(level, 2)
        self.assertEqual(status, "Dérogation")

        # Détection repli par texte
        level, status = parse_conformite(None, None, "Eau d'alimentation conforme aux exigences")
        self.assertEqual(level, 1)
        self.assertEqual(status, "Conforme")

    def test_extract_commune_udi_info(self):
        sample_udis = [
            {
                "nom_commune": "ORLEANS",
                "code_reseau": "045000474",
                "nom_reseau": "RESEAU ANCIEN",
                "debut_alim": "2015-01-01",
                "annee": "2020",
            },
            {
                "nom_commune": "ORLEANS",
                "code_reseau": "045000474",
                "nom_reseau": "RESEAU RECENT",
                "debut_alim": "2020-01-01",
                "annee": "2026",
            },
        ]
        info = extract_commune_udi_info(sample_udis)
        self.assertEqual(info["debut_alim"], "2020-01-01")
        self.assertEqual(info["nom_reseau"], "RESEAU RECENT")

    def test_extract_water_quality_data(self):
        mock_results = [
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1398",
                "libelle_parametre": "Chlore libre",
                "resultat_numerique": 0.11,
                "resultat_alphanumerique": "0,11",
                "libelle_unite": "mg(Cl2)/L",
                "conformite_limites_bact_prelevement": "C",
                "conformite_limites_pc_prelevement": "C",
                "conclusion_conformite_prelevement": "Eau d'alimentation conforme",
            },
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1340",
                "libelle_parametre": "Nitrates (en NO3)",
                "resultat_numerique": 6.30,
                "resultat_alphanumerique": "6,30",
                "libelle_unite": "mg/L",
            },
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1302",
                "libelle_parametre": "pH",
                "resultat_numerique": 7.6,
                "resultat_alphanumerique": "7,6",
                "libelle_unite": "unité pH",
            },
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1303",
                "libelle_parametre": "Conductivité à 25°C",
                "resultat_numerique": 371.0,
                "resultat_alphanumerique": "371",
                "libelle_unite": "µS/cm",
            },
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "7972",
                "libelle_parametre": "Titre hydrotimétrique",
                "resultat_numerique": 13.31,
                "resultat_alphanumerique": "13,31",
                "libelle_unite": "°f",
            },
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1301",
                "libelle_parametre": "Température de l'eau",
                "resultat_numerique": 21.5,
                "resultat_alphanumerique": "21,5",
                "libelle_unite": "°C",
            },
        ]
        udi_info = {
            "nom_commune": "ORLEANS",
            "code_reseau": "045000474",
            "nom_reseau": "ORLEANS CENTRE",
            "debut_alim": "2020-01-01",
        }
        data = extract_water_quality_data(mock_results, udi_info)

        self.assertEqual(data["nitrates"]["value"], 6.30)
        self.assertEqual(data["ph"]["value"], 7.6)
        self.assertEqual(data["conductivite"]["value"], 371.0)
        self.assertEqual(data["durete"]["value"], 13.31)
        self.assertEqual(data["chlore_libre"]["value"], 0.11)
        self.assertEqual(data["temperature"]["value"], 21.5)
        self.assertEqual(data["conformite_status"], "Conforme")
        self.assertEqual(data["conformite_level"], 1)
        self.assertEqual(data["debut_alim_fr"], "01/01/2020")
        self.assertEqual(data["date_prelevement_fr"], "30/07/2026 12:35")


class TestPluginLifecycle(unittest.TestCase):
    """Tests du cycle de vie du plugin Domoticz."""

    def setUp(self):
        import plugin
        plugin.Devices = {}
        plugin.Parameters = {
            "Mode1": "45234",
            "Mode2": "",
            "Mode3": "4",
            "Mode4": "Oui",
            "Mode6": "False",
        }

    @patch("hubeau_client.HubEauClient.get_communes_udi")
    @patch("hubeau_client.HubEauClient.get_resultats_dis")
    def test_plugin_onstart_creates_and_updates_devices(self, mock_dis, mock_udi):
        mock_udi.return_value = [
            {
                "nom_commune": "ORLEANS",
                "code_reseau": "045000474",
                "nom_reseau": "TEST",
                "debut_alim": "2020-01-01",
                "annee": "2026",
            }
        ]
        mock_dis.return_value = [
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1340",
                "libelle_parametre": "Nitrates",
                "resultat_numerique": 5.4,
                "resultat_alphanumerique": "5,4",
                "libelle_unite": "mg/L",
                "conformite_limites_bact_prelevement": "C",
                "conformite_limites_pc_prelevement": "C",
                "conclusion_conformite_prelevement": "Eau conforme",
            }
        ]

        import plugin
        p = plugin.HubEauPlugin()
        p.onStart()

        # Vérification des dispositifs créés
        self.assertIn(UNIT_DATE_ALIM, plugin.Devices)
        self.assertIn(UNIT_DATE_PRELEVEMENT, plugin.Devices)
        self.assertIn(UNIT_NITRATES, plugin.Devices)
        self.assertIn(UNIT_PH, plugin.Devices)
        self.assertIn(UNIT_CONDUCTIVITE, plugin.Devices)
        self.assertIn(UNIT_DURETE, plugin.Devices)
        self.assertIn(UNIT_CHLORE_LIBRE, plugin.Devices)
        self.assertIn(UNIT_TEMPERATURE, plugin.Devices)
        self.assertIn(UNIT_CONFORMITE, plugin.Devices)

        # Vérification des valeurs mises à jour
        self.assertEqual(plugin.Devices[UNIT_DATE_ALIM].sValue, "01/01/2020")
        self.assertEqual(plugin.Devices[UNIT_DATE_PRELEVEMENT].sValue, "30/07/2026 12:35")
        self.assertEqual(plugin.Devices[UNIT_NITRATES].sValue, "5.4")
        self.assertEqual(plugin.Devices[UNIT_CONFORMITE].nValue, 1)

    @patch("hubeau_client.HubEauClient.get_communes_udi")
    @patch("hubeau_client.HubEauClient.get_resultats_dis")
    def test_plugin_resilience_when_udi_fails(self, mock_dis, mock_udi):
        mock_udi.side_effect = HubEauError("Timeout sur communes_udi")
        mock_dis.return_value = [
            {
                "date_prelevement": "2026-07-30T12:35:00Z",
                "code_parametre": "1340",
                "libelle_parametre": "Nitrates",
                "resultat_numerique": 8.1,
                "resultat_alphanumerique": "8,1",
                "libelle_unite": "mg/L",
            }
        ]

        import plugin
        p = plugin.HubEauPlugin()
        p.onStart()

        # Le plugin ne doit pas planter et doit quand même avoir mis à jour les nitrates
        self.assertEqual(plugin.Devices[UNIT_NITRATES].sValue, "8.1")

    def test_heartbeat_trigger(self):
        import plugin
        p = plugin.HubEauPlugin()
        p.poll_interval_hours = 1
        p.heartbeats_required = 120
        p.heartbeat_counter = 119
        
        with patch.object(p, "fetch_and_update") as mock_fetch:
            p.onHeartbeat()
            mock_fetch.assert_called_once()
            self.assertEqual(p.heartbeat_counter, 0)


class TestCommuneResolver(unittest.TestCase):
    """Tests du résolveur de commune via geo.api.gouv.fr."""

    @patch("commune_resolver.CommuneResolver._query")
    def test_resolve_by_insee(self, mock_query):
        from commune_resolver import CommuneResolver
        mock_query.return_value = {
            "nom": "Thionville",
            "code": "57672",
            "codeDepartement": "57",
            "codesPostaux": ["57100"],
        }
        resolver = CommuneResolver()
        sel, alts, msg = resolver.resolve("57672")
        self.assertIsNotNone(sel)
        self.assertEqual(sel["nom"], "Thionville")
        self.assertEqual(sel["code"], "57672")
        self.assertIn("validé", msg)

    @patch("commune_resolver.CommuneResolver._query")
    def test_resolve_by_city_name(self, mock_query):
        from commune_resolver import CommuneResolver
        mock_query.return_value = [
            {
                "nom": "Thionville",
                "code": "57672",
                "codeDepartement": "57",
                "codesPostaux": ["57100"],
            },
            {
                "nom": "Puttelange-lès-Thionville",
                "code": "57557",
                "codeDepartement": "57",
                "codesPostaux": ["57570"],
            },
        ]
        resolver = CommuneResolver()
        sel, alts, msg = resolver.resolve("Thionville")
        self.assertIsNotNone(sel)
        self.assertEqual(sel["nom"], "Thionville")
        self.assertEqual(sel["code"], "57672")
        self.assertEqual(len(alts), 1)
        self.assertIn("résolu vers", msg)


if __name__ == "__main__":
    unittest.main()
