#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "Please run as root"
  echo "$EUID"
  exit 1
fi

apt install libilmbase23 -y
apt install libopenexr-dev -y
apt-get install vim ffmpeg python3 python3-pip libatlas-base-dev v4l2loopback-dkms v4l-utils -y
apt install python3-opencv -y
pip3 install --upgrade pip
pip3 install pynetworktables imutils scikit-build
pip3 install opencv-python

chmod a+x ./setup.sh
./setup.sh
