# Overview
Deployment scripts of Tungsten Fabric CI

# Gerrit deployment
## Initial gerrit service deployment
Initial gerrit host configuration is placed in ansible inventory file
```
all:
  vars:
    gerrit_host: "gerrit.internal"
    gerrit_public_host: "gerrit.external"
    gerrit_ssh_keys: "{{ lookup('env', 'HOME') }}/gerrit/ssh"
    gerrit_force_ssh_keys_generate: true
    gerrit_force_create_zuul_user: true
    gerrit_source_url: "https://review.openstack.org"
    force_update_repos: true
    gerrit_repos:
      - {dest_namespace: "Juniper", project: "zuul", src_namespace: "progmaticlab"}
  children:
    gerrit:
      hosts:
        gerrit.tungsten.io:
      vars:
        gerrit_front_port: 80
```

There are several variables there:
  - **force_update_repos** is used to force recreate gerrit's projects
  - **gerrit_force_create_zuul_user** forces to create *zuul* user in gerrit
  - **gerrit_front_port** stores gerrit webpage port
  - **gerrit_host** stores gerrit internal host name
  - **gerrit_repos** stores list of required repositories to import into gerrit from github.com
  - **gerrit_force_ssh_keys_generate** forces gerrit ssh keys generation
  - **gerrit_ssh_keys** stores local directory path where to store priv\pub keys for gerrit
  - **gerrit_public_host** stores gerrit's external url
  - **gerrit_source_url** stores source URL for all gerrit projects to import from. This URL can be redefined in individual project

To deploy gerrit service, run:
```
    ansible-playbook playbooks/deploy-gerrit.yaml -i hosts.yaml
```

## Import Tunsten Fabric repositories to gerrit
As gerrit service has started on **gerrit_url** you can import official Tunsten Fabric repositories with command:
```
    ansible-playbook playbooks/import-gerrit-repos.yaml -i hosts.yaml
```

# Zuul deployment
## Initial zuul service deployment
Initial zuul host configuration is placed in ansible inventory file
```
all:
  vars:
    gerrit_host: "gerrit.internal"
    gerrit_public_host: "gerrit.external"
    gerrit_ssh_keys: "{{ lookup('env', 'HOME') }}/gerrit/ssh"
  children:
    zuul:
      hosts:
        zuul.tungsten.io:
      vars:
        zuul_front_port: 8080
        zuul_logs_port: 80
```

There are several variables there:
  - **gerrit_host** stores gerrit internal host name
  - **gerrit_ssh_keys** stores local directory path where to store priv\pub keys for gerrit
  - **gerrit_public_host** stores gerrit's external host
  - **zuul_front_port** stores zuul webpage port
  - **zuul_logs_port** stores zuul logs server port

To deploy zuul services, run:
```
    ansible-playbook playbooks/deploy-mysql.yaml -i hosts.yaml
    ansible-playbook playbooks/deploy-zookeeper.yaml -i hosts.yaml
    ansible-playbook playbooks/deploy-nodepool.yaml -i hosts.yaml
    ansible-playbook playbooks/deploy-logserver.yaml -i hosts.yaml
    ansible-playbook playbooks/deploy-zuul.yaml -i hosts.yaml
```

# Nexus deployment
## Initial nexus server deployment
Initial nexus host configuration is placed in ansible inventory file
```
all:
  children:
    nexus:
      hosts:
        192.168.101.56:
```
To deploy nexus service, run:
```
    ansible-playbook playbooks/deploy-nexus.yaml -i hosts.yaml
```

## Mirror yum repositories:
Please see playbooks/roles/nexus/files/nexus-scripting/tfCIRepositories.groovy
for complete list of actual proxied repositories.
