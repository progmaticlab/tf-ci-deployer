#!/bin/bash -e

MIRRORDIR=/repos
DATE=$(date +"%Y%m%d")

mkdir -p ${MIRRORDIR}/ubuntu18/${DATE}
cd ${MIRRORDIR}/ubuntu18

sed -i "s|%MIRRORDIR%|${MIRRORDIR}/ubuntu18/${DATE}|" /etc/apt/mirror.list
apt-mirror && (rm -f stage; ln -s ${DATE} stage)

#Downloading LXD images for juju
mkdir ${DATE}/lxd
cd ${DATE}/lxd
wget -q https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-lxd.tar.xz https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-root.tar.xz
