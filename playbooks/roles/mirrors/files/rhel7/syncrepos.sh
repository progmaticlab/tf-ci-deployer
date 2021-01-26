#!/bin/bash

RHUSERNAME=${RHUSERNAME:-}
RHPASSWORD=${RHPASSWORD:-}
REPOS_RH7=(rhel-7-server-rpms rhel-7-server-optional-rpms rhel-7-server-extras-rpms rhel-7-server-openstack-13-rpms rhel-7-server-openstack-13-devtools-rpms rhel-7-server-ose-3.11-rpms rhel-7-server-ansible-2.6-rpms rhel-7-fast-datapath-rpms rhel-server-rhscl-7-rpms rhel-ha-for-rhel-7-server-rpms rhel-7-server-rhceph-3-tools-rpms)
REPOS_UBI7=(ubi-7 ubi-7-server-debug-rpms ubi-7-server-source-rpms ubi-7-server-optional-rpms ubi-7-server-optional-debug-rpms ubi-7-server-optional-source-rpms ubi-7-server-extras-rpms ubi-7-server-extras-debug-rpms ubi-7-server-extras-source-rpms ubi-7-rhah ubi-7-rhah-debug ubi-7-rhah-source ubi-server-rhscl-7-rpms ubi-server-rhscl-7-debug-rpms ubi-server-rhscl-7-source-rpms ubi-7-server-devtools-rpms ubi-7-server-devtools-debug-rpms ubi-7-server-devtools-source-rpms)
MIRRORDIR=/repos
DATE=$(date +"%Y%m%d")

function unregister_and_exit() {
  subscription-manager unregister
  exit
}

if [[ ! -z ${RHEL_USER+x} && ! -z ${RHEL_PASSWORD+x} && ! -z ${RHEL_POOL_ID+x} ]]; then
  subscription-manager register --name=rhel7repomirror --username=$RHEL_USER --password=$RHEL_PASSWORD
else
  echo "No RedHat subscription credentials provided, exiting"
  exit 1
fi

trap unregister_and_exit EXIT
subscription-manager attach --pool=$RHEL_POOL_ID
yum repolist
yum install -y yum-utils createrepo


for r in ${REPOS_RH7[@]}; do
  subscription-manager repos --enable=${r}
  reposync -l --repoid=${r} --download-metadata --downloadcomps --download_path=${MIRRORDIR}/rhel7/${DATE}
  createrepo -v ${MIRRORDIR}/rhel7/${DATE}/${r}/
done

pushd ${MIRRORDIR}/rhel7
rm -f stage
ln -s ${DATE} stage
popd

for r in ${REPOS_UBI7[@]}; do
  reposync -l --repoid=${r} --download-metadata --downloadcomps --download_path=${MIRRORDIR}/ubi7/${DATE}
  createrepo -v ${MIRRORDIR}/ubi7/${DATE}/${r}/
done

pushd ${MIRRORDIR}/ubi7
rm -f stage
ln -s ${DATE} stage
popd
