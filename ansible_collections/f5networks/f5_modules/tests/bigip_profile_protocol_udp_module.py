#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: bigip_profile_protocol_udp_module

short_description: Ce module permet la modification, suppression ou création d'une vip

description:
  - Se connecte en ssh via paramiko
  - Envoie la ou les commandes sur le device et retourne les lignes affichées par l'équipement.

version_added: '0.1.0'

authors:
  - Theo Laurent (@Theo_Laurent)
  - Benjamin Boussereau (@Benjamin-Boussereau)

options:
  ip:
    description:
      - l'ip de l'équipement sur lequel on souhaite intervenir.
    type: str
    required: true
    
  username:
    description:
      - le login utilisé pour se connecter sur le device.
    type: str
    required: true
    
  password:
    description:
      - le password utilisé pour se connecter sur le device.
    type: str
    required: true
  
  udp_params:
    description:
      - dictionnaire qui contient les informations du profile udp telles qu'écrites dans le fichier.
    type: dict
    required: true
  
'''

EXAMPLES = r'''
- name: Manage the profile protocol udp
  F5Networks.f5-ansible-f5modules.module_bigip_profile_protocol_ucp_module:
    ip = "1.1.1.4"
    username = "myadmin"
    password = "mypass"
    udp_params = "{{udp_params}}"
'''


import paramiko
import sys
import os
import time
import re
from ansible.module_utils.basic import AnsibleModule  

# Foction responsable de l'envoie des commandes ssh sur le server
def fn_ssh(cmdx, server, connection_port, user, pwd):
    # initialisation de la variable de sortie
    output = ""
    # reservation du socket avec le module paramiko SSHClient
    ssh=paramiko.SSHClient()
    # deifinition de la politique de gestion des clé publique des hosts
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # lancement de la connexion ssh sur le server
    ssh.connect(server,connection_port,user,pwd,allow_agent=False,look_for_keys=False)
    # invocation du shell interractif
    shell = ssh.invoke_shell()
    #tempo
    time.sleep(0.5)
    # pour chaque commande de la liste fournie en paramètre divisée sur les retours à la ligne nous lançons cette commande et plaçons le retour du shell dans une variable
    for cm in cmdx.split("\n"):
        cm = cm + "\n"
        shell.send(cm)
        time.sleep(0.5)
        output += shell.recv(65535).decode('utf-8')
    # traitement des résultats pour obtenir une liste lisible
    resp = output.split("\r\n")
    # fermeture du shell et du ssh afin de libérer le socket
    shell.close()
    ssh.close()
    # renvoie de la valeur obtenue
    return(resp)

# Fonction de création d'un profile udp
def fn_creation(udp_params, username, password, ip):
    # Initialisation de la commande principale
    cmd = "tmsh\n"
    cmda = ""
    # Construction des blocs de commande à partir des paramètres udp
    for key in udp_params:
        # On ignore les clés contenant "state"
        if "state" in key:
            pass
        # Commande pour changer de partition
        elif key.strip() == "partition":
            cmd1 = "cd ../" + udp_params[key].strip() + "\n"
        # Commande de création du profil udp
        elif key.strip() == "name":
            cmd2 = "ltm profile udp \ncreate " + udp_params['name'].strip()
        # Ajout des autres paramètres à la commande pour la création
        else:
            cmda = cmda + " " + str(key).strip() + " " + str(udp_params[key]).strip()
    # commande final
    cmd = cmd + cmd1 + cmd2 + cmda
    return(cmd)

# Fonction pour générer une commande de modification d’un profil udp existant
def fn_define_cmd_to_modif(conf_to_modify,udp_params):
    # Début de la commande de modification (tmsh + le profile udp + le nom du profile qu'on veut modif)
    cmd_mod = "tmsh\nltm profile udp\nmodify " + str(udp_params['name'])
    # Ajout des paramètres à modifier
    for modif in conf_to_modify:
        cmd_mod = cmd_mod + " " +  modif
    return(cmd_mod)


# Fonction pour comparer la configuration existante et celle souhaitée dans udps.yml
def fn_compare_conf(udp_params, udp_infos_from_box):
    to_modify = [] # Liste des paramètres à modifier
    # Parcours des lignes de configuration une à une récupérées depuis le boitier
    for udp in range(0,len(udp_infos_from_box),1):
        # On ignore toutes les lignes qui possent problème (message inutil, champs inéxistant dans la GUI)
        if "END" in udp_infos_from_box[udp] or "}" in udp_infos_from_box[udp] or "app-service" in udp_infos_from_box[udp].strip() or "defaults-from" in udp_infos_from_box[udp].strip() or "ip-ttl-v4" in udp_infos_from_box[udp].strip() or "ip-ttl-v6" in udp_infos_from_box[udp].strip() or "no-checksum" in udp_infos_from_box[udp].strip() or "description" in udp_infos_from_box[udp].strip() or udp_infos_from_box[udp] == '' or "Last" in udp_infos_from_box[udp] or "@" in udp_infos_from_box[udp] or "ltm" in udp_infos_from_box[udp]:
          pass
        else:
            # Traitement des lignes contenant "less"
            if "less" in udp_infos_from_box[udp]:
                # On découpe la ligne en utilisant les espaces multiples comme séparateurs
                new_line = re.split(" +",udp_infos_from_box[udp])
                # On récupère le nom du champ et sa valeur depuis la ligne
                udp_field_from_box = new_line[2].strip()
                udp_field_valued_from_box = new_line[3].strip()
                try:
                    # On récupère la valeur attendue depuis udp_params via la découpe de la ligne juste au dessus
                    udp_field_from_file = udp_params[udp_field_from_box]
                    # Si les deux valeurs sont identique on pass
                    if str(udp_field_valued_from_box) == str(udp_field_from_file):
                        pass
                    else:
                        # Si la valeur est différente, on ajoute à la liste des modifications
                        data = udp_field_from_box + " " + str(udp_params[udp_field_from_box])
                        to_modify.append(data)
                # Si le champ n'existe pas dans udp_params, on ignore
                except KeyError:
                    pass
            # Traitement des autres lignes
            else:
                # On découpe la ligne en utilisant seulement un espace comme séparateurs
                udp_field_from_box = udp_infos_from_box[udp].strip().split(' ')[0].strip()
                udp_field_valued_from_box = udp_infos_from_box[udp].strip().split(' ')[1].strip()
                try:
                    # On récupère la valeur attendue depuis udp_params via la découpe de la ligne juste au dessus
                    udp_field_from_file = udp_params[udp_field_from_box]
                    # Si les deux valeurs sont identique on pass
                    if str(udp_field_valued_from_box) == str(udp_field_from_file):
                        pass
                    else:
                        # Si la valeur est différente, on ajoute à la liste des modifications
                        data = udp_field_from_box + " " + str(udp_params[udp_field_from_box])
                        to_modify.append(data)
                # Si le champ n'existe pas dans udp_params, on ignore
                except KeyError:
                    pass
    # Retourne la liste des paramètres à modifier
    return(to_modify)




# Fonction principale chargée de créer, modifier ou supprimer une VIP sur un F5
def main():
    #### On commence par définir le module Ansible et ses paramètres
    module = AnsibleModule( 
        argument_spec=dict(  
            ip      = dict(required=True, type='str'),
            username    = dict(required=True, type='str'),
            password    = dict(required=True, type='str', no_log=True),
            udp_params = dict(required=True, type='dict')
            ) 
        )
    port = 22
    ip = module.params.get('ip') 
    username = module.params.get('username') 
    password = module.params.get('password') 
    udp_params = module.params.get('udp_params')
    # maintenant que nous avons récupéré les informations passées en argument, nous allons observer le contenu de udp_params
    # pour cela, nous lançons une boucle for sur le contenu de la variable et observons l'état du profil udp.
    cmd = "tmsh\ncd ../" + udp_params['partition'] + "\nlist ltm profile udp " + udp_params['name'] + " all-properties\n \n \n \n"
    # Récupération des informations du boîtier via notre fonction SSH
    udp_infos_from_box = fn_ssh(cmd, ip, port, username, password)
    not_found = 0
    # Parcours des lignes de configuration une à une récupérées depuis le boîtier
    for i in range(0, len(udp_infos_from_box),1):
        # Si le profil n'éxiste pas sur le boîtier, alors on ajout 1
        if "not found" in udp_infos_from_box[i]:
            not_found = 1
        # Sinon, on ne fait rien
        else:
            pass
    # Traitement des paramètres du profil udp
    for param in udp_params:
        cmd = ""
        # Gestion de l'état du profil (présent ou absent)
        if param == "state":
            if udp_params[param] != "absent":
                # si le status du profil udp dans le fichier est différent de absent alors nous récupérons les informations de ce dernier sur le     # Parcours des lignes de configuration une à une récupérées depuis le boîtier
                if not_found == 1:
                # Si le profil n'existe pas, on effectue les actions suivantes :
                    creation_profile = fn_creation(udp_params, username, password, ip)
                    # Appel de notre fonction de création
                    action_creation = fn_ssh(creation_profile, ip, port, username, password)
                    # Application sur le boîtier via SSH
                    module.exit_json(changed=True, message="Le profile udp a ete créé", resultat=action_creation)
                else:
                    # Comparaison de la configuration actuelle avec celle souhaitée
                    conf_to_modify = fn_compare_conf(udp_params, udp_infos_from_box)
                    # Ajout des éléments à modifier si des différences existent
                    if conf_to_modify != []:
                        # Si des différences sont détectées, on génère les commandes de modification via notre fonction
                        cmd_to_modify = fn_define_cmd_to_modif(conf_to_modify,udp_params)
                        modification_profile = fn_ssh(cmd_to_modify, ip, port, username, password)
                        # Application sur le boîtier via SSH
                        module.exit_json(changed=True, message="Le profile udp a ete mis à jour", resultat=modification_profile)
                    else:
                        module.exit_json(changed=False, message="Le profile udp sur le boitier est identique à celui du fichier")
            else:
                # vérifier si le profil existe, si oui, lancer la suppression
                if "not found" in udp_infos_from_box:
                    module.exit_json(changed=False, message="Le profile n'existe pas donc nous ne faisons rien")
                else:
                    # commande de suppression
                    suppr_cmd = "tmsh\ncd ../" + udp_params['partition'] + "\nltm profile udp\ndelete " + udp_params['name'] + "\n"
                    # appel fonction fn_ssh avec les commandes de suppression
                    suppression_profile = fn_ssh(suppr_cmd, ip, port, username, password)
                    module.exit_json(changed=False, message="Le profile udp a été supprimé", resultat=suppression_profile)
                    
        # Gestion des des paramètres spécifiques
        elif param in ['idle-timeout', 'ip-tos-to-client', 'link-qos-to-client']:
            # Liste de tous les champs spécifiques
            if udp_params[param]  != "immediate" or udp_params[param] != "indefinite":
                # Si les paramètre on une valeur différente de "immediate" ou de "indefinite"
                udp_params[param] = int(udp_params[param])
                # On force la valeur en int au lieux de str car spécify
            else:
                pass
            # si les champs on comme valeur "immediate" ou "indefinite" on ignore
            
if __name__ == "__main__":
    main()