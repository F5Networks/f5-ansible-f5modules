#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: bigip_profile_client_ssl_module

short_description: Ce module permet la modification, suppression ou création d'un profile client ssl

description:
  - Se connecte en ssh via paramiko
  - Envoie la ou les commandes sur le device et retourne les lignes affichées par l'équipement.

version_added: '0.1.0'

authors:
  - Benjamin Boussereau et Théo Laurent(@Theo_Laurent)

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
  
  clientssl_params:
    description:
      - dictionnaire qui contient les informations du profile clientssl telles qu'écrites dans le fichier.
    type: dict
    required: true
  
'''

EXAMPLES = r'''
- name: Manage the client ssl profile
  F5Networks.f5-ansible-f5modules.module_bigip_profile_client_ssl_module::
    ip = "1.1.1.4"
    username = "myadmin"
    password = "mypass"
    clientssl_params = "{{clientssl_params}}"
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

# Fonction de création d'un profile clientssl
def fn_creation(clientssl_params, username, password, ip):
    # Initialisation de la commande principale
    cmd = "tmsh\n"
    cmda = ""
    # Construction des blocs de commande à partir des paramètres clientssl
    for key in clientssl_params:
        # On ignore les clés contenant "state"
        if "state" in key:
            pass
        # Commande pour changer de partition
        elif key.strip() == "partition":
            cmd1 = "cd ../" + clientssl_params[key].strip() + "\n"
        # Commande de création du profil clientssl
        elif key.strip() == "name":
            cmd2 = "ltm profile client-ssl \ncreate " + clientssl_params['name'].strip()
        # Ajout des autres paramètres à la commande pour la création
        else:
            cmda = cmda + " " + str(key).strip() + " " + str(clientssl_params[key]).strip()
    # commande final
    cmd = cmd + cmd1 + cmd2 + cmda
    return(cmd)

# Fonction pour générer une commande de modification d’un profil clientssl existant
def fn_define_cmd_to_modif(conf_to_modify,clientssl_params):
    # Début de la commande de modification (tmsh + le profile clientssl + le nom du profile qu'on veut modif)
    cmd_mod = "tmsh\nltm profile client-ssl\nmodify " + str(clientssl_params['name'])
    # Ajout des paramètres à modifier
    for modif in conf_to_modify:
        cmd_mod = cmd_mod + " " +  modif
    return(cmd_mod)


# Fonction pour comparer la configuration existante et celle souhaitée dans clientssls.yml
def fn_compare_conf(clientssl_params, clientssl_infos_from_box):
    to_modify = [] # Liste des paramètres à modifier
    # Parcours des lignes de configuration une à une récupérées depuis le boitier
    new_pos = 0
    for clientssl in range(0,len(clientssl_infos_from_box),1):
        # On ignore toutes les lignes qui possent problème (message inutil, champs inéxistant dans la GUI)
        if "END" in clientssl_infos_from_box[clientssl] or "}" in clientssl_infos_from_box[clientssl] or "mpclientssl-debug" in clientssl_infos_from_box[clientssl] or "description" in clientssl_infos_from_box[clientssl].strip() or "defaults-from" in clientssl_infos_from_box[clientssl].strip() or "app-service" in clientssl_infos_from_box[clientssl].strip() or clientssl_infos_from_box[clientssl] == '' or "Last" in clientssl_infos_from_box[clientssl] or "@" in clientssl_infos_from_box[clientssl] or "ltm" in clientssl_infos_from_box[clientssl]:
          pass
        # ensuite si la ligne contient le mot entre double quote
        elif "cert-key-chain" in clientssl_infos_from_box[clientssl]:
            # on initialise une variable string qui recevra le contenu du paramètre dans la condition
            key_chain_params = ""
            # on lance une boucle for en partant de la ligne précédente sur la longueur de la liste, tant que la ligne ne contient pas "cert-lifespan"
            i = clientssl
            new_line = ""
            while "cert-lifespan" not in clientssl_infos_from_box[i].strip():
                if "less" in clientssl_infos_from_box[i].strip():
                    line = clientssl_infos_from_box[i].strip().split(' ')
                    for x in range(1, len(line),1):
                        if line[x] == "" or "%" in line[x]:
                            pass
                        else:
                            if new_line == "" :
                                new_line = line[x]
                            else:
                                new_line = new_line + " " + line[x]
                    if key_chain_params == "":
                        key_chain_params = new_line
                    else:
                        key_chain_params = key_chain_params + " " + new_line
                else:
                    # on ajoute la ligne à la string initialisés plus haut
                    if key_chain_params == "":
                        key_chain_params = clientssl_infos_from_box[i].replace(',','').strip()
                    else:
                        key_chain_params = key_chain_params + " " + clientssl_infos_from_box[i].replace(',','').strip()
                i += 1
            # on récupère la position de la ligne à sur laquelle la boucle s'est stoppé et on ajoute 1 pour avoir la ligne contenant "cert-lifespan"
            new_pos = i + 1
            # si le contenu obtenu est identique à celui présent dans le fichier pour la clé "cert-key-chain" alors on ne fait rien
            compare_chain = "cert-key-chain" + clientssl_params["cert-key-chain"].replace(" ","")
            if key_chain_params.replace(" ","") == compare_chain:
                pass
            else:
                # sinon on construit la var data suivante et on l'ajoute à la liste to_modify
                data = "old = " + key_chain_params + ", new = cert-key-chain " + clientssl_params["cert-key-chain"]
                to_modify.append(data)
        # si la valeur de clientssl est inférieur à la valeur de la ligne obtenu dans la condition ci-dessus, alors clientssl prend cette valeur
        elif clientssl < new_pos:
            clientssl = new_pos
        else:
            # Traitement des lignes contenant "less"
            if "less" in clientssl_infos_from_box[clientssl]:
                # On découpe la ligne en utilisant les espaces multiples comme séparateurs
                new_line = re.split(" +",clientssl_infos_from_box[clientssl])
                # On récupère le nom du champ et sa valeur depuis la ligne
                clientssl_field_from_box = new_line[2].strip()
                clientssl_field_valued_from_box = new_line[3].strip()
                try:
                    # On récupère la valeur attendue depuis clientssl_params via la découpe de la ligne juste au dessus
                    clientssl_field_from_file = clientssl_params[clientssl_field_from_box]
                    # Si les deux valeurs sont identique on pass
                    if str(clientssl_field_valued_from_box) == str(clientssl_field_from_file):
                        pass
                    else:
                        # Si la valeur est différente, on ajoute à la liste des modifications
                        data = clientssl_field_from_box + " " + str(clientssl_params[clientssl_field_from_box])
                        to_modify.append(data)
                # Si le champ n'existe pas dans clientssl_params, on ignore
                except KeyError:
                    pass
            # Traitement des autres lignes
            else:
                # On découpe la ligne en utilisant seulement un espace comme séparateurs
                clientssl_field_from_box = clientssl_infos_from_box[clientssl].strip().split(' ')[0].strip()
                clientssl_field_valued_from_box = clientssl_infos_from_box[clientssl].strip().split(' ')[1].strip()
                try:
                    # On récupère la valeur attendue depuis clientssl_params via la découpe de la ligne juste au dessus
                    clientssl_field_from_file = clientssl_params[clientssl_field_from_box]
                    # Si les deux valeurs sont identique on pass
                    if str(clientssl_field_valued_from_box) == str(clientssl_field_from_file):
                        pass
                    else:
                        # Si la valeur est différente, on ajoute à la liste des modifications
                        data = clientssl_field_from_box + " " + str(clientssl_params[clientssl_field_from_box])
                        to_modify.append(data)
                # Si le champ n'existe pas dans clientssl_params, on ignore
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
            clientssl_params = dict(required=True, type='dict')
            ) 
        )
    port = 22
    ip = module.params.get('ip') 
    username = module.params.get('username') 
    password = module.params.get('password') 
    clientssl_params = module.params.get('clientssl_params')
    # maintenant que nous avons récupéré les informations passées en argument, nous allons observer le contenu de clientssl_params
    # pour cela, nous lançons une boucle for sur le contenu de la variable et observons l'état du profil clientssl.
    cmd = "tmsh\ncd ../" + clientssl_params['partition'] + "\nlist ltm profile client-ssl " + clientssl_params['name'] + " all-properties\n \n \n \n"
    # Récupération des informations du boîtier via notre fonction SSH
    clientssl_infos_from_box = fn_ssh(cmd, ip, port, username, password)
    #module.exit_json(changed=True, message="Le profile clientssl a ete créé", resultat=clientssl_infos_from_box)
    not_found = 0
    # Parcours des lignes de configuration une à une récupérées depuis le boîtier
    for i in range(0, len(clientssl_infos_from_box),1):
        # Si le profil n'éxiste pas sur le boîtier, alors on ajout 1
        if "not found" in clientssl_infos_from_box[i]:
            not_found = 1
        # Sinon, on ne fait rien
        else:
            pass
    # Traitement des paramètres du profil clientssl
    for param in clientssl_params:
        cmd = ""
        # Gestion de l'état du profil (présent ou absent)
        if param == "state":
            if clientssl_params[param] != "absent":
                # si le status du profil clientssl dans le fichier est différent de absent alors nous récupérons les informations de ce dernier sur le     # Parcours des lignes de configuration une à une récupérées depuis le boîtier
                if not_found == 1:
                # Si le profil n'existe pas, on effectue les actions suivantes :
                    creation_profile = fn_creation(clientssl_params, username, password, ip)
                    # Appel de notre fonction de création
                    action_creation = fn_ssh(creation_profile, ip, port, username, password)
                    # Application sur le boîtier via SSH
                    module.exit_json(changed=True, message="Le profile clientssl a ete créé", resultat=action_creation)
                    
                else:
                    # Comparaison de la configuration actuelle avec celle souhaitée
                    conf_to_modify = fn_compare_conf(clientssl_params, clientssl_infos_from_box)
                    # Ajout des éléments à modifier si des différences existent
                    if conf_to_modify != []:
                        # Si des différences sont détectées, on génère les commandes de modification via notre fonction
                        cmd_to_modify = fn_define_cmd_to_modif(conf_to_modify,clientssl_params)
                        modification_profile = fn_ssh(cmd_to_modify, ip, port, username, password)
                        # Application sur le boîtier via SSH
                        module.exit_json(changed=True, message="Le profile clientssl a ete mis à jour", resultat=modification_profile)
                    else:
                        module.exit_json(changed=False, message="Le profile clientssl sur le boitier est identique à celui du fichier")
            else:
                # vérifier si le profil existe, si oui, lancer la suppression
                if "not found" in clientssl_infos_from_box:
                    module.exit_json(changed=False, message="Le profile n'existe pas donc nous ne faisons rien")
                else:
                    # commande de suppression
                    suppr_cmd = "tmsh\ncd ../" + clientssl_params['partition'] + "\nltm profile client-ssl\ndelete " + clientssl_params['name'] + "\n"
                    # appel fonction fn_ssh avec les commandes de suppression
                    suppression_profile = fn_ssh(suppr_cmd, ip, port, username, password)
                    module.exit_json(changed=True, message="Le profile clientssl a été supprimé", resultat=suppression_profile)
                    
        # Gestion des des paramètres spécifiques
        elif param in ['alert-timeout', 'handshake-timeout', 'renegotiate-period', 'renegotiate-size', 'renegotiate-max-record-delay', 'max-active-handshakes', 'max-aggregate-renegotiation-per-minute']:
            # Liste de tous les champs spécifiques
            if clientssl_params[param]  != "immediate" or clientssl_params[param] != "indefinite":
                # Si les paramètre on une valeur différente de "immediate" ou de "indefinite"
                clientssl_params[param] = int(clientssl_params[param])
                # On force la valeur en int au lieux de str car spécify
            else:
                pass
            # si les champs on comme valeur "immediate" ou "indefinite" on ignore
            
if __name__ == "__main__":
    main()