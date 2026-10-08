# Plugin Domoticz - Qualité de l'Eau Potable (Hub'Eau)

Ce plugin pour [Domoticz](https://www.domoticz.com/) permet de surveiller la qualité de l'eau potable distribuée dans votre commune en interrogeant directement l'API officielle française [Hub'Eau - Qualité de l'eau potable](https://hubeau.eaufrance.fr/page/api-qualite-eau-potable).

Les données proviennent des résultats du contrôle sanitaire officiel de l'eau du robinet réalisé par les Agences Régionales de Santé (ARS), consolidées dans la base SISE-Eaux du Ministère de la Santé et publiées sur data.gouv.fr / Hub'Eau.

---

## 📋 Tuiles créées dans Domoticz

Le plugin crée et met à jour automatiquement les dispositifs suivants :

### Tuiles principales (demandées)
1. **Date dernière alimentation** : Date de début d'alimentation du réseau / unité de distribution (UDI) de la commune *(Dispositif Texte)*.
2. **Date dernier prélèvement** : Date et heure du dernier contrôle sanitaire enregistré *(Dispositif Texte)*.
3. **Nitrates** : Teneur en nitrates en $mg/L$ (Code Sandre `1340`) *(Capteur personnalisé, unité mg/L)*.
4. **Potentiel Hydrogène (pH)** : Mesure du pH de l'eau (Code Sandre `1302`) *(Capteur personnalisé ou pH)*.
5. **Conductivité** : Conductivité électrique à 25 °C en $\mu S/cm$ (Code Sandre `1303`) *(Capteur personnalisé, unité µS/cm)*.
6. **Dureté de l'eau** : Titre hydrotimétrique (TH) en degrés français $°f$ (Code Sandre `7972`) *(Capteur personnalisé, unité °f)*.
7. **Chlore libre** : Teneur en chlore libre en $mg(Cl_2)/L$ (Code Sandre `1398`) *(Capteur personnalisé, unité mg/L)*.
8. **Température au prélèvement** : Température de l'eau mesurée sur le terrain lors du prélèvement en $°C$ (Code Sandre `1301`) *(Capteur Température)*.

### Tuiles complémentaires
9. **Conformité sanitaire** : Statut global de conformité du prélèvement (chimique et bactériologique) avec code couleur Domoticz *(Dispositif Alerte : Vert = Conforme, Jaune/Orange = Dérogation / Avertissement, Rouge = Non conforme)*.
10. **Conclusion sanitaire** : Texte officiel de la conclusion sanitaire rédigée par l'ARS *(Dispositif Texte)*.
11. **Chlore total** : Teneur en chlore total en $mg(Cl_2)/L$ (Code Sandre `1399`) *(Capteur personnalisé, unité mg/L)*.
12. **Turbidité** : Turbidité néphélométrique en NFU (Code Sandre `1295`) *(Capteur personnalisé, unité NFU)*.

---

## ⏱️ Fréquence de rafraîchissement des données

### Comment sont mises à jour les données Hub'Eau ?
* **Publication Hub'Eau / Ministère de la Santé** : Les données nationales SISE-Eaux sont consolidées et republiées par l'API Hub'Eau selon un rythme **mensuel**.
* **Prélèvements sur le terrain (ARS)** : La fréquence des prélèvements réels en commune dépend du Code de la santé publique (taille de la population desservie, débit du réseau, historique et vulnérabilité de la ressource). Une grande métropole peut faire l'objet de plusieurs analyses par semaine, tandis qu'une petite commune rurale peut être contrôlée mensuellement ou trimestriellement.

### Recommandation d'intervalle dans Domoticz
Puisque les données changent à l'échelle de quelques jours à plusieurs semaines, un appel permanent est inutile. Le plugin propose par défaut un rafraîchissement toutes les **4 heures** (ou configurable : 1h, 2h, 4h, 12h, 24h). Cela garantit :
* Une détection rapide dès qu'un nouveau rapport d'analyse est publié.
* Un respect parfait des quotas et serveurs de l'API Hub'Eau.

---

## ⚙️ Configuration du plugin

Lors de l'ajout du matériel dans Domoticz :
* **Code INSEE de la commune** *(Obligatoire)* : Code officiel INSEE sur 5 chiffres de votre commune (ex: `45234` pour Orléans, `75056` pour Paris, `69123` pour Lyon). *Attention, il s'agit du code INSEE et non du code postal.*
* **Code Réseau / UDI** *(Optionnel)* : Si votre commune est desservie par plusieurs réseaux de distribution d'eau, vous pouvez spécifier ici le code réseau (ex: `045000474`). Si laissé vide, le plugin utilise automatiquement le premier réseau actif identifié.
* **Intervalle de vérification** : Fréquence de scrutation de l'API (ex: 4 heures).
* **Créer les tuiles complémentaires** : Option (Vrai / Faux) pour activer les tuiles additionnelles (Conformité Alerte, Conclusion sanitaire, Chlore total, Turbidité).
* **Mode Debug** : Active les traces détaillées dans les logs Domoticz pour le diagnostic.

---

## 📦 Installation

1. Accédez au répertoire des plugins de votre installation Domoticz :
   ```bash
   cd domoticz/plugins
   ```
2. Clonez ce dépôt :
   ```bash
   git clone https://github.com/<votre-compte>/domoticz-hubeau.git Domoticz-HubEau
   ```
3. Redémarrez le service Domoticz :
   ```bash
   sudo systemctl restart domoticz
   ```
4. Dans l'interface Web de Domoticz, rendez-vous dans le menu **Réglages > Matériel** (Setup > Hardware).
5. Dans la liste déroulante des types de matériel, choisissez **Hub'Eau - Qualité de l'eau potable**.
6. Renseignez votre **Code INSEE**, ajustez vos options et cliquez sur **Ajouter**.

---

## 🛠️ Dépendances

* Python **3.8+**
* Aucune dépendance externe obligatoire : le client utilise la bibliothèque standard Python (`urllib.request`, `json`). Compatible nativement avec Raspberry Pi OS, Debian, Ubuntu, Windows et Docker.
