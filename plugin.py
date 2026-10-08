#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
<plugin key="HubEauDrinkingWater" name="Hub'Eau - Qualité de l'eau potable" author="Arnaud" version="1.0.0" wikilink="https://hubeau.eaufrance.fr/page/api-qualite-eau-potable">
    <description>
        <h2>Hub'Eau - Qualité de l'eau potable</h2>
        <p>Ce plugin interroge l'API officielle publique <b>Hub'Eau</b> (Ministère de la Santé / BRGM / Agences de l'eau) afin de suivre la qualité de l'eau potable distribuée dans votre commune.</p>
        <p>Il met à disposition des indicateurs clés : date de prélèvement, date de mise en alimentation de l'UDI, nitrates, pH, conductivité, dureté, chlore libre, température et statut de conformité sanitaire.</p>
        <p><b>Note sur la fréquence :</b> La base nationale est mise à jour mensuellement et les prélèvements ARS varient selon la taille de la commune. Un intervalle de 4 à 12 heures est recommandé.</p>
    </description>
    <params>
        <param field="Mode1" label="Code INSEE de la commune" width="120px" required="true" default="45234"/>
        <param field="Mode2" label="Code Réseau / UDI (optionnel)" width="140px" required="false" default=""/>
        <param field="Mode3" label="Fréquence de rafraîchissement" width="160px" required="true" default="4">
            <options>
                <option label="Toutes les heures" value="1"/>
                <option label="Toutes les 2 heures" value="2"/>
                <option label="Toutes les 4 heures" value="4" default="true"/>
                <option label="Toutes les 6 heures" value="6"/>
                <option label="Toutes les 12 heures" value="12"/>
                <option label="Toutes les 24 heures" value="24"/>
            </options>
        </param>
        <param field="Mode4" label="Tuiles complémentaires" width="100px" required="true" default="Oui">
            <options>
                <option label="Oui (Conformité, Conclusion, Turbidité, Chlore total)" value="Oui" default="true"/>
                <option label="Non (Tuiles principales uniquement)" value="Non"/>
            </options>
        </param>
        <param field="Mode6" label="Mode Debug" width="75px">
            <options>
                <option label="Vrai" value="True"/>
                <option label="Faux" value="False" default="true"/>
            </options>
        </param>
    </params>
</plugin>
"""

import sys
from typing import Any, Dict, Optional

try:
    import Domoticz  # type: ignore
except ImportError:
    # Mock pour test hors environnement Domoticz
    class MockDevice:
        def __init__(self, Name: str, Unit: int, Type: int = 0, Subtype: int = 0, TypeName: str = "", Options: Optional[Dict] = None, Used: int = 1) -> None:
            self.Name = Name
            self.Unit = Unit
            self.Type = Type
            self.Subtype = Subtype
            self.TypeName = TypeName
            self.Options = Options or {}
            self.Used = Used
            self.nValue = 0
            self.sValue = ""

        def Create(self) -> "MockDevice":
            global Devices
            if "Devices" in globals():
                Devices[self.Unit] = self
            print(f"  [Device Created] Unit {self.Unit}: '{self.Name}' ({self.TypeName or f'T={self.Type}/S={self.Subtype}'})")
            return self

        def Update(self, nValue: int, sValue: str) -> None:
            self.nValue = nValue
            self.sValue = sValue
            print(f"  [Device Update] Unit {self.Unit} ({self.Name}) -> nValue={nValue}, sValue='{sValue}'")

    class MockDomoticz:
        def __init__(self) -> None:
            self.Device = MockDevice
            self.Debugging = lambda x: print(f"[Domoticz Debugging]: {x}")
            self.Log = lambda msg: print(f"[LOG] {msg}")
            self.Debug = lambda msg: print(f"[DEBUG] {msg}")
            self.Error = lambda msg: print(f"[ERROR] {msg}")
            self.Status = lambda msg: print(f"[STATUS] {msg}")

    Domoticz = MockDomoticz()

from data_parser import extract_commune_udi_info, extract_water_quality_data
from hubeau_client import HubEauClient, HubEauError

# Identifiants stables des unités Domoticz
UNIT_DATE_ALIM = 1
UNIT_DATE_PRELEVEMENT = 2
UNIT_NITRATES = 3
UNIT_PH = 4
UNIT_CONDUCTIVITE = 5
UNIT_DURETE = 6
UNIT_CHLORE_LIBRE = 7
UNIT_TEMPERATURE = 8
# Tuiles complémentaires
UNIT_CONFORMITE = 9
UNIT_CONCLUSION = 10
UNIT_CHLORE_TOTAL = 11
UNIT_TURBIDITE = 12


class HubEauPlugin:
    """Plugin Domoticz pour le suivi de la qualité de l'eau potable via Hub'Eau."""

    def __init__(self) -> None:
        self.code_commune = ""
        self.code_reseau = ""
        self.poll_interval_hours = 4
        self.include_extra_tiles = True
        self.debug_mode = False
        self.client = HubEauClient(timeout=30)
        self.heartbeat_counter = 0
        self.heartbeats_required = 480  # 4h * 120 (30s par battement)

    def onStart(self) -> None:
        """Initialisation au démarrage du matériel dans Domoticz."""
        global Parameters, Devices

        if "Parameters" in globals():
            params = Parameters
        else:
            params = {}

        self.debug_mode = params.get("Mode6", "False").lower() in ("true", "1", "vrai")
        if self.debug_mode:
            Domoticz.Debugging(1)
            Domoticz.Debug("Mode Debug activé pour Hub'Eau.")

        self.code_commune = str(params.get("Mode1", "")).strip()
        self.code_reseau = str(params.get("Mode2", "")).strip()
        
        try:
            self.poll_interval_hours = max(1, int(params.get("Mode3", 4)))
        except (ValueError, TypeError):
            self.poll_interval_hours = 4

        self.include_extra_tiles = params.get("Mode4", "Oui") == "Oui"

        # Calcul du nombre de heartbeats (Domoticz appelle onHeartbeat ~toutes les 30s)
        # 1 heure = 3600s / 30s = 120 battements
        self.heartbeats_required = self.poll_interval_hours * 120
        self.heartbeat_counter = self.heartbeats_required  # Pour forcer une mise à jour immédiate au démarrage

        Domoticz.Log(
            f"Démarrage du plugin Hub'Eau (Commune INSEE: '{self.code_commune}', "
            f"Réseau: '{self.code_reseau or 'Auto'}', Intervalle: {self.poll_interval_hours}h)"
        )

        if not self.code_commune:
            Domoticz.Error("Code INSEE non configuré. Veuillez renseigner le Mode1 dans la configuration.")
            return

        self._create_devices()
        self.fetch_and_update()

    def _create_device_if_missing(
        self,
        unit: int,
        name: str,
        type_name: str,
        options: Optional[Dict[str, str]] = None,
        type_id: Optional[int] = None,
        subtype_id: Optional[int] = None,
    ) -> None:
        """Crée un dispositif Domoticz s'il n'existe pas encore dans Devices."""
        global Devices
        devices_dict = globals().get("Devices", {})

        if unit not in devices_dict:
            Domoticz.Debug(f"Création du dispositif Unit {unit}: {name} ({type_name})")
            if type_id is not None and subtype_id is not None:
                Domoticz.Device(
                    Name=name,
                    Unit=unit,
                    Type=type_id,
                    Subtype=subtype_id,
                    Options=options or {},
                    Used=1,
                ).Create()
            elif type_name:
                Domoticz.Device(
                    Name=name,
                    Unit=unit,
                    TypeName=type_name,
                    Options=options or {},
                    Used=1,
                ).Create()

    def _create_devices(self) -> None:
        """Crée l'ensemble des tuiles requises et optionnelles."""
        # 1. Date dernière alimentation
        self._create_device_if_missing(
            unit=UNIT_DATE_ALIM,
            name="Eau - Dernière alimentation UDI",
            type_name="Text",
        )
        # 2. Date dernier prélèvement
        self._create_device_if_missing(
            unit=UNIT_DATE_PRELEVEMENT,
            name="Eau - Dernier prélèvement",
            type_name="Text",
        )
        # 3. Nitrates
        self._create_device_if_missing(
            unit=UNIT_NITRATES,
            name="Eau - Nitrates",
            type_name="Custom",
            options={"Custom": "1;mg/L"},
        )
        # 4. Potentiel Hydrogène (pH)
        self._create_device_if_missing(
            unit=UNIT_PH,
            name="Eau - Potentiel Hydrogène (pH)",
            type_name="Custom",
            options={"Custom": "1;pH"},
        )
        # 5. Conductivité
        self._create_device_if_missing(
            unit=UNIT_CONDUCTIVITE,
            name="Eau - Conductivité",
            type_name="Custom",
            options={"Custom": "1;µS/cm"},
        )
        # 6. Dureté de l'eau
        self._create_device_if_missing(
            unit=UNIT_DURETE,
            name="Eau - Dureté (TH)",
            type_name="Custom",
            options={"Custom": "1;°f"},
        )
        # 7. Chlore libre
        self._create_device_if_missing(
            unit=UNIT_CHLORE_LIBRE,
            name="Eau - Chlore libre",
            type_name="Custom",
            options={"Custom": "1;mg/L"},
        )
        # 8. Température au prélèvement
        self._create_device_if_missing(
            unit=UNIT_TEMPERATURE,
            name="Eau - Température prélèvement",
            type_name="Temperature",
        )

        # Tuiles complémentaires
        if self.include_extra_tiles:
            # 9. Conformité sanitaire (Alerte: 1=Conforme/Vert, 2=Dérogation, 4=Non conforme/Rouge)
            self._create_device_if_missing(
                unit=UNIT_CONFORMITE,
                name="Eau - Conformité sanitaire",
                type_name="Alert",
            )
            # 10. Conclusion sanitaire
            self._create_device_if_missing(
                unit=UNIT_CONCLUSION,
                name="Eau - Conclusion sanitaire",
                type_name="Text",
            )
            # 11. Chlore total
            self._create_device_if_missing(
                unit=UNIT_CHLORE_TOTAL,
                name="Eau - Chlore total",
                type_name="Custom",
                options={"Custom": "1;mg/L"},
            )
            # 12. Turbidité
            self._create_device_if_missing(
                unit=UNIT_TURBIDITE,
                name="Eau - Turbidité",
                type_name="Custom",
                options={"Custom": "1;NFU"},
            )

    def _update_device(self, unit: int, n_value: int, s_value: str) -> None:
        """Met à jour un dispositif si sa valeur a changé."""
        global Devices
        devices_dict = globals().get("Devices", {})

        if unit in devices_dict:
            dev = devices_dict[unit]
            s_val = str(s_value)
            # Met à jour uniquement si changement de nValue ou sValue
            if dev.nValue != n_value or dev.sValue != s_val:
                Domoticz.Debug(f"Mise à jour Unit {unit} ({dev.Name}) : nValue={n_value}, sValue='{s_val}'")
                dev.Update(nValue=n_value, sValue=s_val)

    def fetch_and_update(self) -> None:
        """Interroge l'API Hub'Eau et met à jour l'ensemble des tuiles."""
        if not self.code_commune:
            Domoticz.Error("Code INSEE non configuré.")
            return

        Domoticz.Log(f"Interrogation de l'API Hub'Eau pour la commune {self.code_commune}...")

        try:
            udis = self.client.get_communes_udi(self.code_commune)
            udi_info = extract_commune_udi_info(udis, self.code_reseau)

            # Si aucun code réseau configuré, mais qu'un réseau a été identifié
            active_reseau = self.code_reseau or udi_info.get("code_reseau")
            results = self.client.get_resultats_dis(
                code_commune=self.code_commune,
                code_reseau=active_reseau or None,
                size=50,
            )

            data = extract_water_quality_data(results, udi_info)
            self._apply_data(data)
            Domoticz.Log("Données Hub'Eau mises à jour avec succès.")

        except HubEauError as err:
            Domoticz.Error(f"Erreur lors de la récupération Hub'Eau : {err}")
        except Exception as err:
            Domoticz.Error(f"Erreur inattendue dans fetch_and_update : {err}")

    def _apply_data(self, data: Dict[str, Any]) -> None:
        """Applique les données extraites aux dispositifs Domoticz."""
        # 1. Date dernière alimentation
        date_alim = data.get("debut_alim_fr") or data.get("debut_alim") or "Non renseignée"
        self._update_device(UNIT_DATE_ALIM, 0, str(date_alim))

        # 2. Date dernier prélèvement
        date_prelev = data.get("date_prelevement_fr") or data.get("date_prelevement") or "Aucun prélèvement"
        self._update_device(UNIT_DATE_PRELEVEMENT, 0, str(date_prelev))

        # 3. Nitrates
        nitrates = data.get("nitrates")
        if nitrates and nitrates.get("value") is not None:
            self._update_device(UNIT_NITRATES, 0, str(nitrates["value"]))

        # 4. Potentiel Hydrogène (pH)
        ph = data.get("ph")
        if ph and ph.get("value") is not None:
            self._update_device(UNIT_PH, 0, str(ph["value"]))

        # 5. Conductivité
        cond = data.get("conductivite")
        if cond and cond.get("value") is not None:
            self._update_device(UNIT_CONDUCTIVITE, 0, str(cond["value"]))

        # 6. Dureté de l'eau
        durete = data.get("durete")
        if durete and durete.get("value") is not None:
            self._update_device(UNIT_DURETE, 0, str(durete["value"]))

        # 7. Chlore libre
        chlore_l = data.get("chlore_libre")
        if chlore_l and chlore_l.get("value") is not None:
            self._update_device(UNIT_CHLORE_LIBRE, 0, str(chlore_l["value"]))

        # 8. Température au prélèvement
        temp = data.get("temperature")
        if temp and temp.get("value") is not None:
            self._update_device(UNIT_TEMPERATURE, 0, str(temp["value"]))

        # Tuiles complémentaires
        if self.include_extra_tiles:
            # 9. Conformité sanitaire (Alerte)
            level = data.get("conformite_level", 0)
            status = data.get("conformite_status", "Inconnu")
            self._update_device(UNIT_CONFORMITE, level, str(status))

            # 10. Conclusion sanitaire
            conclusion = data.get("conclusion") or "Aucune conclusion enregistrée"
            self._update_device(UNIT_CONCLUSION, 0, str(conclusion))

            # 11. Chlore total
            chlore_t = data.get("chlore_total")
            if chlore_t and chlore_t.get("value") is not None:
                self._update_device(UNIT_CHLORE_TOTAL, 0, str(chlore_t["value"]))

            # 12. Turbidité
            turb = data.get("turbidite")
            if turb and turb.get("value") is not None:
                self._update_device(UNIT_TURBIDITE, 0, str(turb["value"]))

    def onHeartbeat(self) -> None:
        """Appelé par Domoticz toutes les 30 secondes."""
        self.heartbeat_counter += 1
        if self.heartbeat_counter >= self.heartbeats_required:
            self.heartbeat_counter = 0
            Domoticz.Debug("Déclenchement du rafraîchissement périodique Hub'Eau...")
            self.fetch_and_update()

    def onStop(self) -> None:
        """Appelé lors de l'arrêt du plugin ou de Domoticz."""
        Domoticz.Log("Arrêt du plugin Hub'Eau.")

    def onCommand(self, Unit: int, Command: str, Level: int, Hue: int) -> None:
        """Gestion des commandes reçues (lecture seule, non applicable)."""
        Domoticz.Debug(f"onCommand appelé pour Unit {Unit}: Command={Command}, Level={Level}")


global _plugin
_plugin = HubEauPlugin()


def onStart() -> None:
    global _plugin
    _plugin.onStart()


def onStop() -> None:
    global _plugin
    _plugin.onStop()


def onHeartbeat() -> None:
    global _plugin
    _plugin.onHeartbeat()


def onCommand(Unit: int, Command: str, Level: int, Hue: int) -> None:
    global _plugin
    _plugin.onCommand(Unit, Command, Level, Hue)


if __name__ == "__main__":
    # Test autonome en ligne de commande
    code = sys.argv[1] if len(sys.argv) > 1 else "45234"
    print(f"=== Test autonome plugin Hub'Eau pour la commune {code} ===")
    
    # Simulation des globals Domoticz
    Parameters = {
        "Mode1": code,
        "Mode2": "",
        "Mode3": "4",
        "Mode4": "Oui",
        "Mode6": "True",
    }
    Devices = {}
    
    _plugin = HubEauPlugin()
    _plugin.onStart()
    print("=== Test terminé avec succès ===")
