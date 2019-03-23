# Overview
Deployment scripts of Tungsten Fabric CI

# Gerrit deployment
## Initial gerrit service deployment

Initial gerrit host configuration is placed in ansible inventory file
```
all:
  vars:
    gerrit_url: "http://gerrit.tungsten.io"
  children:
    gerrit:
      hosts:
        gerrit.tungsten.io:
      vars:
        force_update_repos: true
```

There are several variables there:
  - **gerrit_url** is used to set gerrit's external url
  - **force_update_repos** is used to force recreate gerrit's projects

To deploy gerrit service, run:
```
    ansible-playbook playbooks/deploy-gerrit.yaml -i hosts.yaml
```

## Import Tunsten Fabric repositories to gerrit
As gerrit service has started on **gerrit_url** you can import official Tunsten Fabric repositories with command:
```
    ansible-playbook playbooks/import-gerrit-repos.yaml -i hosts.yaml
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