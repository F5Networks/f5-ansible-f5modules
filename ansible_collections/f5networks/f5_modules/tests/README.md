# Ansible Collection - F5Networks.bigip_module

In this fork we have placed all the custom modules that we have developed.
We did this beacuse the ones in the well known collection had not enough details.
We decided to develop the same modules but we added all the parameters presents in the device.
All the modules are GitOps oriented.

Available modules
-------------------

bigip_profile_client_ssl_module : Module made to manage the profile client ssl. It accept in parameter a variable named "clientssl_params" containing all the informations 
for the profile. The state of the profile ("present" = creation or update, "absent" = delete) is defined in the git file
bigip_profile_persistence_hash : Module made to manage the profile persistence Hash.
bigip_profile_protocol_sslserver_module :  Module made to manage the profile server ssl. It accept in parameter a variable named "sslserver_params" containing all the
informations for the profile. The state of the profile ("present" = creation or update, "absent" = delete)  is defined in the git file
bigip_profile_protocol_tcp_module :  Module made to manage the profile TCP. It accept in parameter a variable named "tcp_params" containing all the
informations for the profile. The state of the profile ("present" = creation or update, "absent" = delete)  is defined in the git file
bigip_profile_protocol_udp_module : Module made to manage the profile UDP. It accept in parameter a variable named "udp_params" containing all the
informations for the profile. The state of the profile ("present" = creation or update, "absent" = delete)  is defined in the git file
bigip_virtual_server_module : Module made to manage the Virtual server in the device. It accept in parameter a variable named "vip_params" containing all the
informations for the profile. The state of the profile ("present" = creation or update, "absent" = delete)  is defined in the git file 

Examples:       
---------

- Managing a client ssl profile:
   - name: Client SSl profile creation/suppression/update
     F5Networks.bigip_modules.bigip_profiles_client_ssl_module:
       ip : "1.1.1.4"
       username : "{{my_username}}"
       password : "{{my_password}}"
       clientssl_params : "{{profile_client_ssl_params_from_git_file}}"

- Managing a server ssl profile:
   - name: Server SSl profile creation/suppression/update
     F5Networks.bigip_modules.bigip_profiles_server_ssl_module:
       ip : "1.1.1.4"
       username : "{{my_username}}"
       password : "{{my_password}}"
       sslserver_params : "{{profile_server_ssl_params_from_git_file}}"

- Managing a profile persistence hash:
    - name: profile hash management
      F5Networks.bigip_modules.bigip_profile_persistence_hash:  
        description : "this profile is a test" 
        ip : "1.1.1.4"
        username : "{{my_username}}"
        password : "{{my_password}}"
        hash_name :"{{hash_profile_test}}"
        partition : "{{hash_profile_partition_on_the_device}}
        hash_algorithm : "{{default or CARP}}"
        hash_length : "{{length_of_hash_as_integer}}"
        hash_buffer_limit : "{{max_size_of_the_hash_buffer}}"
        hash_offset : "{{hash_offset_size}}"
        irule : "{{name_of_the_irule}}"
        timeout : "{{timeout_as_integer}}"
        state : "{{profile_state: asbent, present}}"

- Managing a profile tcp:
    - name: tcp profile managment
      F5Networks.bigip_modules.bigip_profile_protocol_tcp_module:  
        ip : "1.1.1.4"
        username : "{{my_username}}"
       password : "{{my_password}}"
       tcp_params : "{{profile_tcp_params_from_git_file}}"

- Managing a profile udp:
    - name: udp profile managment
      F5Networks.bigip_modules.bigip_profile_protocol_udp_module:  
        ip : "1.1.1.4"
        username : "{{my_username}}"
       password : "{{my_password}}"
       udp_params : "{{profile_udp_params_from_git_file}}"

- Managing a virtual server:
    - name: virtual server managment
      F5Networks.bigip_modules.bigip_virtual_server_module:  
        ip : "1.1.1.4"
        username : "{{my_username}}"
       password : "{{my_password}}"
       vip_params : "{{virtual_server_params_from_git_file}}"


License
-------

BSD

Author Information
------------------

Benjamin Boussereau (MAIF external)
Theo Laurent (MAIF trainee)

