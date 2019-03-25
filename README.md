# Overview
Deployment scripts of Tungsten Fabric CI

# Gerrit deployment
## Initial gerrit service deployment
Initial gerrit host configuration is placed in ansible inventory file
```
all:
  vars:
    gerrit_host: "http://gerrit.tungsten.io"
    gerrit_url: "http://{{ gerrit_host }}"
    gerrit_ssh_keys: "{{ lookup('env', 'HOME') }}/gerrit/ssh"
    gerrit_ssh_keys_generate: true
    gerrit_create_zuul_user: true
    gerrit_repos:
      - {dest_namespace: "Juniper", project: "zuul", src_namespace: "progmaticlab"}
  children:
    gerrit:
      hosts:
        gerrit.tungsten.io:
      vars:
        force_update_repos: true
        gerrit_front_port: 80
```

There are several variables there:
  - **force_update_repos** forces to recreate already existing gerrit projects
  - **force_update_repos** is used to force recreate gerrit's projects
  - **gerrit_create_zuul_user** forces to create *zuul* user in gerrit
  - **gerrit_front_port** stores gerrit webpage port
  - **gerrit_host** stores gerrit host name
  - **gerrit_repos** stores list of required repositories to import into gerrit from github.com
  - **gerrit_ssh_keys_generate** forces gerrit ssh keys generation
  - **gerrit_ssh_keys** stores local directory path where to store priv\pub keys for gerrit
  - **gerrit_url** stores gerrit's external url

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
    gerrit_host: "gerrit.tungsten.io"
    gerrit_url: "http://{{ gerrit_host }}"
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
  - **gerrit_host** stores gerrit host name
  - **gerrit_ssh_keys** stores local directory path where to store priv\pub keys for gerrit
  - **gerrit_url** stores gerrit's external url
  - **zuul_front_port** stores zuul webpage port
  - **zuul_logs_port** stores zuul logs server port

To deploy zuul service, run:
```
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
Name | Target URL
------- | ---------------- |
centos74-updates | https://mirror.yandex.ru/centos/7/updates/x86_64/
centos74-extras | https://mirror.yandex.ru/centos/7/extras/x86_64/
centos74 | http://mirror.yandex.ru/centos/7/os/x86_64/
epel | http://mirror.yandex.ru/epel/7/x86_64/
yum-tungsten-tpc | http://148.251.5.90/tpc