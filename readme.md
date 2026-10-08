# Domoticz Hub'Eau - Qualité de l'Eau Potable

[![Domoticz](https://img.shields.io/badge/Domoticz-Compatible-blue.svg)](https://www.domoticz.com/)
[![Python](https://img.shields.io/badge/Python-3.8%2B-brightgreen.svg)](https://www.python.org/)
[![API Hub'Eau](https://img.shields.io/badge/API-Hub'Eau%20Eau%20Potable-informational.svg)](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable)
[![API Géo](https://img.shields.io/badge/API-geo.api.gouv.fr-blueviolet.svg)](https://geo.api.gouv.fr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Plugin Python pour **[Domoticz](https://www.domoticz.com/)** permettant de suivre la qualité de l'eau potable du robinet en France via l'API publique officielle **[Hub'Eau](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable)** (Ministère de la Santé / BRGM / Agences de l'eau).

Les données proviennent directement des résultats du contrôle sanitaire officiel de l'eau distribuée réalisés par les Agences Régionales de Santé (ARS), consolidées dans la base SISE-Eaux.

---

## 🚀 Fonctionnalités clés

* **Résolution intelligente de la commune** : Vous pouvez saisir directement le **nom de votre ville** (ex: *Paris*, *Lyon*, *Orléans*) ou votre **code postal** (ex: *75001*, *69001*). Le plugin résout et valide automatiquement le code officiel INSEE via l'API nationale `geo.api.gouv.fr`.
* **Nommage contextualisé des dispositifs** : Les tuiles créées intègrent automatiquement le nom officiel de votre ville (ex: `Eau (Orléans) - Nitrates`).
* **Zéro dépendance tierce** : Développé exclusivement avec les modules standards de Python (`urllib.request`, `json`, `datetime`). Aucune commande `pip install` n'est requise.
* **Tolérance aux pannes et résilience** : Gestion des indisponibilités temporaires ou lenteurs des serveurs publics avec conservation des dernières mesures connues et reprises automatiques.

---

## 📊 Tuiles créées dans Domoticz

Le plugin crée automatiquement des dispositifs dédiés dans Domoticz :

### Tuiles principales
| Dispositif | Type Domoticz | Code Sandre | Unité | Description |
|---|---|:---:|:---:|---|
| **Dernière alimentation UDI** | Text | - | Date | Date de mise en service du réseau de distribution |
| **Dernier prélèvement** | Text | - | Date/Heure | Date et heure du dernier contrôle sanitaire ARS |
| **Nitrates** | Custom Sensor | `1340` | $mg/L$ | Teneur en nitrates ($NO_3$) |
| **Potentiel Hydrogène (pH)** | Custom Sensor | `1302` | $pH$ | Mesure de l'acidité / basicité de l'eau |
| **Conductivité** | Custom Sensor | `1303` | $\mu S/cm$ | Conductivité électrique à 25 °C |
| **Dureté de l'eau (TH)** | Custom Sensor | `7972` | $°f$ | Titre hydrotimétrique en degrés français |
| **Chlore libre** | Custom Sensor | `1398` | $mg/L$ | Chlore actif désinfectant |
| **Température prélèvement** | Temperature | `1301` | $°C$ | Température relevée au point de captage |

### Tuiles complémentaires (activables dans les réglages)
| Dispositif | Type Domoticz | Code Sandre | Unité | Description |
|---|---|:---:|:---:|---|
| **Conformité sanitaire** | Alert | - | Statut | 🟢 Vert (Conforme), 🟡 Jaune (Dérogation), 🔴 Rouge (Non conforme) |
| **Conclusion sanitaire** | Text | - | Texte | Avis sanitaire officiel rédigé par l'ARS |
| **Chlore total** | Custom Sensor | `1399` | $mg/L$ | Chlore combiné et libre total |
| **Turbidité** | Custom Sensor | `1295` | $NFU$ | Clarté et transparence de l'eau |

---

## ⏱️ Fréquence de rafraîchissement des données

* **Rythme de publication Hub'Eau** : Les données nationales de contrôle sanitaire sont publiées et consolidées **mensuellement**.
* **Prélèvements sur le terrain (ARS)** : La fréquence réglementaire des prélèvements dépend de la taille de la population desservie et du débit des installations (de plusieurs fois par semaine pour les grandes métropoles à quelques semaines ou mois pour les petites communes).
* **Intervalle recommandé** : Un rafraîchissement toutes les **4 heures** (paramètre par défaut) permet de détecter un nouveau rapport dès sa mise en ligne sans solliciter inutilement les serveurs de l'API.

---

## 📦 Installation

### 1. Cloner le dépôt
Accédez au répertoire `plugins` de votre installation Domoticz :

```bash
cd domoticz/plugins
git clone https://github.com/J0hnMatrix/domoticz-hubeau.git Domoticz-HubEau
```

*(Sous Linux, assurez-vous des droits d'exécution si nécessaire : `chmod +x Domoticz-HubEau/plugin.py`)*

### 2. Redémarrer Domoticz
```bash
sudo systemctl restart domoticz
```

### 3. Ajouter le matériel
1. Ouvrez l'interface web de Domoticz.
2. Allez dans **Réglages > Matériel** (*Setup > Hardware*).
3. Sélectionnez le type : **Hub'Eau - Qualité de l'eau potable**.
4. Renseignez les paramètres et cliquez sur **Ajouter**.

---

## ⚙️ Paramètres de configuration

| Paramètre | Description | Défaut |
|---|---|:---:|
| **Commune** | Nom de la ville (ex: `Orléans`), code postal (ex: `45000`) ou code INSEE (ex: `45234`). | `Paris` |
| **Code Réseau / UDI** | Code réseau spécifique si la commune comporte plusieurs réseaux (optionnel). | *(Automatique)* |
| **Fréquence** | Intervalle entre chaque vérification (1h, 2h, 4h, 6h, 12h, 24h). | `4 heures` |
| **Tuiles complémentaires** | Active les tuiles d'alerte conformité, avis sanitaire, chlore total et turbidité. | `Oui` |
| **Mode Debug** | Affiche les traces détaillées dans le journal Domoticz. | `Faux` |

---

## 🧪 Tests autonomes

Le plugin inclut une suite de tests unitaires et peut également être exécuté directement en ligne de commande en dehors de Domoticz :

```bash
# Lancement de la suite de tests unitaires
python -m unittest discover tests -v

# Test autonome en direct avec une commune (nom, code postal ou INSEE)
python plugin.py Orléans
python plugin.py 69001
```

---

## 📄 Licence

Ce projet est distribué sous licence MIT. Consultez le fichier [LICENSE](LICENSE) pour plus de détails.
