#!/bin/bash -e

REPOS_RH8=(rhel-8-for-x86_64-appstream-rpms rhel-8-for-x86_64-baseos-rpms rhel-8-for-x86_64-highavailability-rpms ansible-2.9-for-rhel-8-x86_64-rpms ansible-2-for-rhel-8-x86_64-rpms advanced-virt-for-rhel-8-x86_64-rpms satellite-tools-6.5-for-rhel-8-x86_64-rpms openstack-16.1-for-rhel-8-x86_64-rpms fast-datapath-for-rhel-8-x86_64-rpms rhceph-4-tools-for-rhel-8-x86_64-rpms)
REPOS_UBI8=(ubi-8-appstream ubi-8-baseos ubi-8-codeready-builder)
MIRRORDIR=/repos
DATE=$(date +"%Y%m%d")

function unregister_and_exit() {
  subscription-manager unregister
  exit
}

if [[ ! -z ${RHEL_USER+x} && ! -z ${RHEL_PASSWORD+x} && ! -z ${RHEL_POOL_ID+x} ]]; then
  subscription-manager register --name=rhel8repomirror --username=$RHEL_USER --password=$RHEL_PASSWORD
else
  echo "No RedHat subscription credentials provided, exiting"
  exit 1
fi

trap unregister_and_exit EXIT
subscription-manager attach --pool=$RHEL_POOL_ID
yum repolist
yum install -y yum-utils createrepo


for r in ${REPOS_RH8[@]}; do
  subscription-manager repos --enable=${r}
  reposync --repoid=${r} --download-metadata --downloadcomps --download-path=${MIRRORDIR}/rhel8/${DATE}
  createrepo -v ${MIRRORDIR}/rhel8/${DATE}/${r}/
done

pushd ${MIRRORDIR}/rhel8
rm -f stage
ln -s ${DATE} stage
popd

for r in ${REPOS_UBI8[@]}; do
  reposync --repoid=${r} --download-metadata --downloadcomps --download-path=${MIRRORDIR}/ubi8/${DATE}
  createrepo -v ${MIRRORDIR}/ubi8/${DATE}/${r}/
done

pushd ${MIRRORDIR}/ubi8
rm -f stage
ln -s ${DATE} stage
popd
