#!/bin/bash

username='admin'
password='admin123'
url='http://localhost:8081'
create_update_groovy_script='complex-script/addUpdateScript.groovy'
grape_config='complex-script/grapeConfig.xml'
debug='false'

function usage() {
    printf "$0"
    printf "Configure TF CI Nexus tool\\n"
    printf "Options:\\n"
    printf "\\t[--username $username]\\n"
    printf "\\t[--password $password]\\n"
    printf "\\t[--url $url]\\n"
    printf "\\t[--create_update_groovy_script $create_update_groovy_script]\\n"
    printf "\\t[--grape_config $grape_config]\\n"
    printf "\\t[--debug]\\n"
}

while [[ -n "$1" ]] ; do
    case $1 in
        '--username')
            username="$2"
            ;;
        '--password')
            password="$2"
            ;;
        '--url')
            url="$2"
            ;;
        '--create_update_groovy_script')
            create_update_groovy_script="$2"
            ;;
        '--grape_config')
            grape_config="$2"
            ;;
        '--debug')
            debug="true"
            shift 1
            continue
            ;;
        *)
            echo "ERROR: unknown options '$1'"
            usage
            exit -1
            ;;
    esac
    shift 2
done

[[ "${debug}" == 'true' ]] && set -x

function create_and_run_script {
  local name=$1
  local file=$2
  # using grape config that points to local Maven repo and Central Repository , default grape config fails on some downloads although artifacts are in Central
  # change the grapeConfig file to point to your repository manager, if you are already running one in your organization
  groovy \
    -Dgroovy.grape.report.downloads=true \
    -Dgrape.config=$grape_config \
    $create_update_groovy_script \
    -u "$username" -p "$password" -n "$name" -f "$file" -h "$url"
  printf "\nPublished $file as $name with result $?\n\n"
  # Run script
  curl -v -X POST -u $username:$password \
    --header "Content-Type: text/plain" \
    "$url/service/rest/v1/script/$name/run"
  printf "\nExecuted $name script with result $?\n\n\n"
}

create_and_run_script tfci_repos tfCIRepositories.groovy
create_and_run_script tfci_roles tfCIRoles.groovy
