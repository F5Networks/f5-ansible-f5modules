#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

DOCUMENTATION = r'''
---
module: bigip_virtual_server_module

short_description: Ce module permet la modification, suppression ou création d'une vip

description:
  - Se connecte en ssh via paramiko
  - Envoie la ou les commandes sur le device et retourne les lignes affichées par l'équipement.

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
  
  vip_params:
    description:
      - dictionnaire qui contient les informations de la vip telles qu'écrites dans le fichier.
    type: dict
    required: true
  
'''

EXAMPLES = r'''
- name: Manage the virtual server
  F5Networks.f5-ansible-f5modules.module_bigip_virtual_server_module:
    ip = "1.1.1.4"
    username = "myadmin"
    password = "mypass"
    vip_params = "{{vip_params}}"
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
    

# fonction responsable de la construction de la commande à envoyé pour créer une vip
def fn_define_cmd_and_send_it(vip, user, pwd, server):
    # on commence par initialiser la var cmd.
    cmd = "tmsh\n"
    cmdx = ""
    output = []
    # ensuite, on va lancer la boucle
    for v in vip:
        print(v)
        if "state" in v or "syn-cookie-status" in v:
            pass
        elif v.strip() == "partition":
            cmd1 = "cd ../"+ vip[v].strip() + "\n"
        elif v.strip()=="name":
            cmd2 = "ltm virtual\ncreate " + vip[v].strip()
        elif v.strip() == "profiles":
            cmdp = " profiles add " + str(vip[v]).strip().replace("'","")
        elif v.strip() == "source-address-translation":
            cmds = " source-address-translation " + str(vip[v]).strip().replace("'","")
        elif v.strip()=="vlans-disabled" or v.strip()=="vlans-enabled":
            cmdv = " " + str(v).strip()
        else:
            cmdx = cmdx + " " + str(v).strip() + " " + str(vip[v]).strip()
    cmd = cmd + cmd1 + cmd2 + cmdp + cmds + cmdv + cmdx
    return(cmd)


# définition de la fonction permettant la construction des commandes de modification
def fn_cmd_to_modif(list_modif, vip_name, partition):
    cmd_mod = "tmsh\nltm virtual\ncd ../"+partition+"\nmodify " + str(vip_name)
    for modif in list_modif:
        cmd_mod = cmd_mod + " " +  modif
    return(cmd_mod)


# cette focntion à pour objectif de comparer la conf de la vip sur le boitier à sa conf dans le fichier
# elle retourne soit une liste contenant les actions de création et le chiffre 1 comme suit : 1,vip_creation
# soit elle retourne une liste contenant tous les champs à modifier sur le boitier. (nommée to_modify)
def fn_verif_vip_conf(conf_vip_box, conf_vip_file, username, password, ip, port):
    to_modify = []
    # pour chaque ligne retournée par la commande ssh
    new_pos = 0
    new_pos_2 = 0
    for pos in range(0,len(conf_vip_box),1):
        # si la ligne contient "not found", nous lançons les actions de création car cela indique que la VIP n'existe pas
        if "not found" in conf_vip_box[pos]:
            action_on_vip = fn_define_cmd_and_send_it(conf_vip_file, username, password, ip)
            vip_creation = fn_ssh(action_on_vip,ip, port, username,password)
            data = [1, vip_creation]
            return(data)
        # sinon si profiles est dans la ligne
        elif conf_vip_box[pos].strip().split(' ')[0] == "profiles" :
            profile_params = ""
            profile_pos = pos
            i = pos
            # nous lançons une autre boucle sur le contenu obtenu sur le boitier en commençant à l'index
            # de la ligne comprenant "profiles"
            # tant que la ligne ne contient pas rate-class, nous ajoutons le contenu de la ligne dans la var
            while  "rate-class" not in conf_vip_box[i]:
                profile_params = profile_params + conf_vip_box[i].strip()
                last_pos = i
                i += 1
            # ensuite nous récupérons l'index de la dernière ligne et ajoutons 1 de sorte de recommencer à la ligne
            # contenant "rate-class"
            new_pos = i + 1
            # maintenant si le contenu récupérer sur le boitier est identique à celui du fichier pour le champs profile
            # nous ne faison rien, sinon nous ajoutons le champs du fichiers à la var to_modify
            if profile_params.replace('profiles','').strip() == conf_vip_file['profiles']:
                continue
            else:
                data = "profiles replace " + conf_vip_file['profiles']
                to_modify.append(data)
        # si la valeur de la position en cours est inférieur à celle définie dans la boucle précédente, nous lui donnons cette valeur
        elif pos < new_pos:
            pos = new_pos
        # Dans le même cas que pour le champs profiles, nous vérifions si la ligne contient le mot suivant
        elif conf_vip_box[pos].strip().split(' ')[0] == "source-address-translation" :
            snat_params = ""
            profile_pos = pos
            i = pos
            # si oui, nous suivons les mêmes étapes que pour profiles
            while  "source-port" not in conf_vip_box[i]:
                snat_params = snat_params + conf_vip_box[i].strip()
                last_pos = i
                i += 1
            new_pos_2 = i + 1
            if snat_params == conf_vip_file['source-address-translation']:
                continue
            else:
                data = "source-address-translation " + conf_vip_file['source-address-translation']
                to_modify.append(data)
        # dans ce cas, si la postion dans la liste à laquelle nous sommes rendues est comprise entre la new_pos obtenue
        # dans la boucle profiles et la nouvelle pos obtenu dans la boucle juste au dessus, nous lui donnons la plus grande
        elif new_pos <pos < new_pos_2:
            pos = new_pos_2
        # si tmos est dans la ligne ou que la ligne contient creation-time ou modified-time nous ne la traitons pas
        elif "Last" in conf_vip_box[pos] or "@" in conf_vip_box[pos] or "tmos" in conf_vip_box[pos] or "creation-time" in conf_vip_box[pos] or "last-modified-time" in conf_vip_box[pos] or "ltm" in conf_vip_box[pos] or "}" in conf_vip_box[pos] or "{" in conf_vip_box[pos] or "END" in conf_vip_box[pos] or "less" in conf_vip_box[pos] or "vs-index" in conf_vip_box[pos].strip():
            pass
        # si la ligne contient "vlans-disabled" et que le contenu du fichier est le même alors nous ne faisons rien
        elif "vlans-disabled" in conf_vip_box[pos]:
            if conf_vip_file['vlans-disabled']:
                pass
            # sinon nous plaçons le contenu du fichier dans la var to_modify
            elif conf_vip_file['vlans-enabled']:
                to_modify.append('vlans-enabled')
        # idem mais avec "vlans-enabled"
        elif "vlans-enabled" in conf_vip_box[pos]:
            if conf_vip_file['vlans-disabled']:
                to_modify('vlans-disabled')
            elif conf_vip_file['vlans-enabled']:
                pass
        # ensuite, si la ligne est égale à enabled et que le champs state du fichier y est égal alors nous ne faisons rien
        elif conf_vip_box[pos].strip() == "enabled" or conf_vip_box[pos].strip() == "disabled":
            if conf_vip_file['state'] == conf_vip_box[pos].strip() and conf_vip_file['state'] != "absent":
                pass
            # sinon nous ajoutons le status dans la var to_modify
            else:
                to_modify.append(conf_vip_file['state'])
        # si destination est dans la ligne
        elif "destination" in conf_vip_box[pos]:
            # nous récupérons l'ip, le protocol et ensuite formatons les deux ensemble
            ip_dest = conf_vip_box[pos].strip().split(' ')[1].split(':')[0].split('%')[0]
            prot_dest = conf_vip_box[pos].strip().split(' ')[1].split(':')[1]
            formated_dest = ip_dest+":"+str(prot_dest)
            ip_dest_from_file = conf_vip_file['destination']
            # ensuite si l'ip formaté est égale à celle du fichier, nous ne faison rien, sinon nous ajoutons l'ip du fichier dans la var
            if formated_dest == ip_dest_from_file:
                pass
            else:
                data = "destination " + ip_dest_from_file
                to_modify.append(data)
        # enfin si la ligne ne match aucune des conditions précédentes,
        else:
            # nous récupérons le champs de la ligne (avant l'espace) et sa valeur (après l'espace)
            vip_info_value = conf_vip_box[pos].strip().split(' ')[1]
            vip_info_key = conf_vip_box[pos].strip().split(' ')[0]
            # Nous comparons ensuite la valeur avec celle du champs dans le fichier
            # si identique, nous ne faisons rien
            # sinon nous ajoutons le champs du fichier
            if vip_info_value == conf_vip_file[vip_info_key]:
                pass
            else:
                data = vip_info_key + " " + str(conf_vip_file[vip_info_key])
                to_modify.append(data)
    return(to_modify)


# fonction principale chargé de créer, modifier ou supprimer une vip sur un F5
def main():
    #### On commence par définir le module ansible et ses paramètres
    module = AnsibleModule( 
        argument_spec=dict(  
            ip      = dict(required=True, type='str'),
            username    = dict(required=True, type='str'),
            password    = dict(required=True, type='str', no_log=True),
            vip_params = dict(required=True, type='dict')
            ) 
        )
    port = 22
    ip = module.params.get('ip') 
    username = module.params.get('username') 
    password = module.params.get('password') 
    vip_params = module.params.get('vip_params')
    # maintenant que nous avons récupérer les informations passées en argument, nous allons observer le contenu de vip_params
    # nous commençons par récupérer les infors de la vip si elle existe
    cmd = "tmsh\ncd ../" + vip_params['partition'] + "\nlist ltm virtual " + vip_params['name'] + " all-properties\n \n \n \n"
    vip_infos_from_box = fn_ssh(cmd, ip, port, username, password)
    # ensuite nous observons le champs "state" de la liste vip_params
    if vip_params['state'] != "absent":
        # si le status de la vip dans le fichier est différent de absent alors nous comparons la conf du boitier et celle du fichier
        verif_vip_config = fn_verif_vip_conf(vip_infos_from_box, vip_params, username, password, ip, port)
        # si le retour de la comparaison est une liste contenant 1 et une liste de phrase, alors nous savons
        # que la vip vient d'être créée sur le boitier
        if type(verif_vip_config) == list and verif_vip_config[0] == 1:
            module.exit_json(changed=False, message="la vip a été créée", resultat=verif_vip_config[1])
        # sinon si le retour contient une liste non vide, alors nous savons qu'il existe des différences
        # ce faisant nous appelons la fonction fn_cmd_to_modif pour obtenir une phrase contenant les commandes
        # à entrer dans le boitier. Nous utilisons ensuite fn_ssh pour envoyé ces commandes
        elif verif_vip_config != []:
            action_to_modif = fn_cmd_to_modif(verif_vip_config,vip_params['name'], vip_params['partition'])
            vip_modification = fn_ssh(action_to_modif,ip,port,username,password)
            module.exit_json(changed=False, resultat=vip_modification)
        # si le retour est une liste vide alors nous savons que les conf sont identiques.
        else:
            module.exit_json(changed=False, message="la conf de la vip sur le boitier est identique a celle du fichier")
    elif vip_params['state'] == "absent":
        # si la vip n'existe pas sur le boitier nous affichons le message suivant
        if "not found" in vip_infos_from_box:
            module.exit_json(changed=False, message="la vip n'est pas présente sur le boitier donc nous ne faisons rien'")
        # sinon nous lançons les actions de suppression
        else:
            cmd = "tmsh\ncd ../" + vip_params['partition'] + "\nltm virtual\ndelete " + vip_params['name'] + "\n"
            suppression_vip = fn_ssh(cmd,ip,port,username,password)
            module.exit_json(changed=False, resultat=suppression_vip)

if __name__ == "__main__":
    main()