# Business - Orchestrator

L'orchestrateur sert à administrer le réseau "industriel" des machines du Fablab.
Actuellement il n'y a que des machines 3D Prusa.
Certaines plus anciennes, d'autres plus récentes.
Les machines plus récentes disposent nativement de PrusaLink, les plus anciennes peuvent être "augmentées" avec une RaspberryPi 0 et un Os créé par Prusa afinde les connecter à ce réseau.

Seul l'orchestrateur sera exposé sur l'extérieur du réseau.

## Fonctionnalités métier:
- Explorer le réseau "indus" et détecter les machines qui y sont connectées.
- Détecter si une machine expose un contrat d'interface connu (Prusalink)
- Associer une machine du réseau indus à un id métier (manuel) et persister cette information
- Marquer une machine du réseau comme devant être ignorée
- Mettre à jour ou supprimer cette association
- Lister toutes les machines existantes sur le réseau
- Lister toutes les associations réalisées ( mac, ip, id métier, ignoré )
- A partir des informations réseau, mettre à jour l'ip des associations si elle a changé pour une même mac (mac = source de vérité)
- Envoyer une impression sur une machine à partir de son id métier
- Recueillir les informations d'une machine du réseau respectant le contrat d'interface (statut d'utilisation/offline, température, job en cours, ...)
- Lister en temps quasi réel les informations des machines du réseau respectant le contrat d'interface 

## API exposée:
- Lister les constantes vitales ( statut d'utilisation, % complétion job en cours,  ) des machines associées à un id métier
- Envoyer une demande d'impression à partir d'un id métier
