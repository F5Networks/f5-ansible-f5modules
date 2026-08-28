#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: module_bigip_persistence_hash

short_description: Ce module permet la MAJ (creation/Suppression/modification d'une persitence type cookie-session hash)

description:
  - Se connecte en ssh via paramiko
  - Envoie les commandes de configuration du prolie persistence cookie-session hash.
  - Affiche les actions réalisées

version_added: '0.1.0'

authors:
  - Benjamin Boussereau (@Benjamin-Boussereau)
  - Theo Laurent (@Theo_Laurent)

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
  
  hash_name:
    description:
	  - le nom du persistence profile
	type: str
	required: true

  partition:
    description: 
	  - la partition sur laquelle se trouve le profile
	type: str
	required: true
  
  hash_algorithm:
    description:
	  - l'alogithme de chiffrement utilisé par le profile pour générer le hash (default_value = default)
	type: bool
	required: false

  hash_length:
    description:
	  - la longueur du hash à configurer (default: 0)
	type: int
	required: false

  hash_offset:
    description:
	  - by default 0
	type: int
	required: false

  irule:
    description:
	  - la règle irule sur laquelle se base le profile pour calculer le hash (default: None)
	type: str
	required: false

  timeout:
	description:
	  - temps max de connexion avant de relancer le calcul du hash (default: 180)
	type: int
	required: false
'''

EXAMPLES = r'''
- name: configure un profile persistence hash
  F5Networks.f5-ansible-f5modules.module_bigip_persistence_hash:
    state: "present"
	ip: "ip_du_f5"
	username: "toto"
	password: "secret"
	hash_name: "test_hash"
    partition: "Admin"
    hash_algorithm: "myAlgo"
    hash_buffer_limit: "64634"
    hash_length: "128"
    hash_offset: "10"
    timeout = "300"
    irule = "None"
'''


import paramiko
import sys
import os
import time
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


# fonction principale chargé de créer, modifier ou supprimer une persistence de type hash sur un F5
def main():
    # initialisation des paramètre attendu par le module et de leur type ainsi que de leur valeur par defaut
    module = AnsibleModule( 
        argument_spec=dict( 
            description     = dict(required=True, type='str'), 
            ip      = dict(required=True, type='str'),
            username    = dict(required=True, type='str'),
            password    = dict(required=True, type='str', no_log=True),
            hash_name    = dict(required=True, type='str'),
            partition    = dict(required=True, type='str', default="Common"),
            hash_algorithm    = dict(required=False, type='str', default="default"),
            hash_length    = dict(required=False, type='int', default=0),
            hash_buffer_limit    = dict(required=False, type='int', default=0),
            hash_offset    = dict(required=False, type='int',default=0),
            irule    = dict(required=False, type='str',default=None),
            timeout    = dict(required=False, type='int', default=180),
            state = dict(required=False, type='str'),
            no_log = dict(type='bool', required=False, default=False)
            ) 
        )
    # on récupère les informations fournies dans le module et on les place dans des variables
    port = 22
    description = module.params.get('description') 
    ip = module.params.get('ip') 
    username = module.params.get('username') 
    password = module.params.get('password') 
    hash_name = module.params.get('hash_name') 
    partition = module.params.get('partition') 
    hash_algorithm = module.params.get('hash_algorithm') 
    hash_length = module.params.get('hash_length') 
    hash_buffer_limit = module.params.get('hash_buffer_limit') 
    hash_offset = module.params.get('hash_offset') 
    irule = module.params.get('irule') 
    timeout = module.params.get('timeout') 
    state = module.params.get('state') 
    # on place les premières commandes de bases dans les deux var suivantes
    cmd0 = "tmsh\ncd ../" + partition + "\n"
    cmd1 = "ltm persistence hash\n"
    # ensuite, si le status du profile est "present" nous commençons par vérifier son existence sur le boitier
    if state == "present":
        cmd2 = "list "+ hash_name + "\n"
        cmd= cmd0 + cmd1 + cmd2
        profile_existence = fn_ssh(cmd, ip, port, username, password)
        # s'il n'existe pas, nous lançons les commandes de création
        if "not found" in profile_existence:
            cmd2 = "create " + hash_name+ " defaults-from hash description "+ description + " hash-buffer-limit " + str(hash_buffer_limit) +" hash-length " + str(hash_length)+ " hash-offset "+str(hash_offset)+ " hash-algorithm " + hash_algorithm+ " timeout "+str(timeout) + " rule " + irule +"\n"
            cmd = cmd0 + cmd1 + cmd2
        # sinon, nous récupérons sa configuration et, pour chaque élément vérifions si sa valeur est égale ou non à celle du fichier source
        # si ce n'est pas le cas nous plaçons ce champs de configuration dans la liste "to_modify"
        else:
            to_modify = []
            for line in profile_existence:
                if "description" in line:
                    if line.split("description")[1].strip() != description:
                        data = " description " + description
                        to_modify.append(data)
                elif "hash-buffer-limit" in line:
                    if line.split("hash-buffer-limit")[1].strip() != hash_buffer_limit:
                        data = " hash-buffer-limit " + hash_buffer_limit
                        to_modify.append(data)
                elif "hash-length" in line:
                    if line.split("hash-length")[1].strip() != hash_length:
                        data = " hash-length " + hash_length
                        to_modify.append(data)
                elif "hash-offset" in line:
                    if line.split("hash-offset")[1].strip() != hash_offset:
                        data = " hash-offset " + hash_offset
                        to_modify.append(data)
                elif "hash-algorithm" in line:
                    if line.split("hash-algorithm")[1].strip() != hash_algorithm:
                        data = " hash-algorithm " + hash_algorithm
                        to_modify.append(data)
                elif "timeout" in line:
                    if line.split("timeout")[1].strip() != timeout:
                        data = " timeout " + timeout
                        to_modify.append(data)
                elif "rule" in line:
                    if line.split("rule")[1].strip() != irule:
                        data = " rule " + irule
                        to_modify.append(data)
            # si la liste suivante est vide, nous quittons le module en precisant le message suivant car le hash est identique au fichier source
            if to_modify == []:
                module.exit_json(changed=False, message="pas de modifications à apporter au hash")
            # sinon nous allons lancer les commandes de modifications sur le boitier
            else:
                cmd2 = "modify " + hash_name
                for i in range(0, len(to_modify), 1):
                    cmd2 = cmd2 + to_modify[i]
                cmd2 = cmd2 + "\n"
                cmd = cmd0 + cmd1 + cmd2
        action_on_profile = fn_ssh(cmd, ip, port, username, password)
    # sinon si le status du profile sur le fichier source est "absent" nous lançons les commandes de suppression.
    elif state == "absent":
        cmd2 = "delete " + hash_name + "\n"
        cmd = cmd0 + cmd1 + cmd2
        action_on_profile = fn_ssh(cmd, ip, port, username, password)
    # enfin nous quittons le module en retournant les actions réalisées sur le F5
    module.exit_json(changed=True, resultat=action_on_profile)

if __name__ == "__main__":
    main()