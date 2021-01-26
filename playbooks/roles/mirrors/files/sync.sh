#!/bin/bash

[ $# -ne 1 ] && exit 1

DIST=$1
BASEDIR=/var/local/mirror/repos/

. /root/rhpwd

envopts=""
if [[ ! -z ${RHEL_USER+x} && ! -z ${RHEL_PASSWORD+x} && ! -z ${RHEL_POOL_ID+x} ]] ; then
  envopts="-e RHEL_USER=${RHEL_USER} -e RHEL_PASSWORD=${RHEL_PASSWORD} -e RHEL_POOL_ID=${RHEL_POOL_ID}"
fi

docker run --rm --name ${DIST}repos -v ${BASEDIR}:/repos ${envopts} ${DIST}repos
