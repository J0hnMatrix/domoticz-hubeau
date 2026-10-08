# Directives et Guide d'Architecture pour Agents

Ce document détaille l'architecture technique, les contrats d'API, les conventions de code et les procédures de tests pour le développement et la maintenance du plugin Domoticz Hub'Eau.

---

## 1. Objectif du projet

Fournir un plugin Python pour la solution domotique **Domoticz** permettant de monitorer la qualité de l'eau potable en France via l'API publique officielle **Hub'Eau** (Ministère de la Santé / BRGM / Agences de l'eau).

---

## 2. Architecture logicielle

Pour assurer une testabilité maximale sans dépendance au moteur C++ de Domoticz, le projet est découpé en trois couches :

```
domoticz-hubeau/
├── hubeau_client.py   # Client API Hub'Eau pur (HTTP urllib standard, sans dépendance externe)
├── data_parser.py     # Extraction, typage et normalisation des paramètres de prélèvement
├── plugin.py          # Adaptateur Domoticz (cycle de vie onStart, onHeartbeat, création/mise à jour de Devices)
├── test_hubeau.py     # Suite de tests unitaires et d'intégration autonomes
├── readme.md          # Documentation utilisateur
├── agents.md          # Guide technique et règles d'ingénierie
└── .gitignore         # Fichiers et dossiers ignorés par Git
```

### Avantages de ce découpage :
* `hubeau_client.py` et `data_parser.py` peuvent être testés via `pytest` ou `python test_hubeau.py` sans mock complexe du moteur Domoticz.
* `plugin.py` intègre un mock léger de l'objet global `Domoticz` pour permettre son exécution directe en CLI pour le debug.
* Zéro dépendance tierce requise sur le serveur Domoticz (utilisation de `urllib.request`, `json`, `datetime` de la bibliothèque standard Python).

---

## 3. Spécifications de l'API Hub'Eau

### Endpoints utilisés :
* **Informations UDI / Réseau** :
  `GET https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/communes_udi?code_commune={insee}`
  Permet d'extraire le nom de la commune, le code réseau, le nom du réseau et la date de début d'alimentation (`debut_alim`).
* **Résultats des prélèvements** :
  `GET https://hubeau.eaufrance.fr/api/v1/qualite_eau_potable/resultats_dis?code_commune={insee}&size=100&sort=desc`
  Filtre optionnel sur `code_reseau={code_reseau}`.

### Correspondance des codes paramètres (SANDRE) :
| Paramètre | Code Sandre | Unité Domoticz | Type Domoticz Device |
|-----------|-------------|----------------|----------------------|
| Potentiel Hydrogène (pH) | `1302` | `pH` | Custom Sensor (Options: `1;pH`) |
| Conductivité à 25°C | `1303` | `µS/cm` | Custom Sensor (Options: `1;µS/cm`) |
| Nitrates (en NO3) | `1340` | `mg/L` | Custom Sensor (Options: `1;mg/L`) |
| Titre hydrotimétrique (Dureté) | `7972` (ou libellé contenant "hydrotimétrique") | `°f` | Custom Sensor (Options: `1;°f`) |
| Chlore libre | `1398` | `mg/L` | Custom Sensor (Options: `1;mg/L`) |
| Chlore total | `1399` | `mg/L` | Custom Sensor (Options: `1;mg/L`) |
| Turbidité | `1295` | `NFU` | Custom Sensor (Options: `1;NFU`) |
| Température de l'eau | `1301` | `°C` | Temperature (Type=80) |
| Date dernière alimentation | - | Texte | Text (Type=243, SubType=19) |
| Date dernier prélèvement | - | Texte | Text (Type=243, SubType=19) |
| Conformité sanitaire | - | Alerte | Alert (Type=243, SubType=22) |
| Conclusion sanitaire | - | Texte | Text (Type=243, SubType=19) |

---

## 4. Stratégie de mise à jour des dispositifs Domoticz

* **Unit IDs stables** : Chaque indicateur dispose d'un index d'unité fixe (`Unit` 1 à 12).
* **Mise à jour conditionnelle** : Pour éviter d'écrire des logs inutiles et de déclencher des événements Domoticz superflus, une mise à jour d'un device n'est transmise que si sa valeur (`nValue` ou `sValue`) a changé, ou si l'intervalle configuré est atteint.
* **Gestion du heartbeat** : Domoticz invoque `onHeartbeat()` environ toutes les 30 secondes. Un compteur interne calcule l'écoulement du temps en fonction de l'intervalle en heures configuré par l'utilisateur.

---

## 5. Conventions de commit (Conventional Commits)

Les messages de commit doivent respecter le format :
`<type>(<scope optionnel>): <description en minuscules>`

Types autorisés :
* `feat`: Nouvelle fonctionnalité ou tuile
* `fix`: Correction de bug ou gestion d'anomalie
* `refactor`: Refonte de code sans changement fonctionnel
* `test`: Ajout ou ajustement de tests unitaires
* `docs`: Documentation, README, agents.md
* `chore`: Maintenance, .gitignore, configurations

Chaque modification fonctionnelle validée doit faire l'objet d'un commit atomique.
