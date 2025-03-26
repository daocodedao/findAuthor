#!/bin/sh


/data/work/Anycast/anycast.sh  --status


p='127.0.0.1:1087'
git config --global http.proxy $p
git config --global https.proxy $p

export http_proxy=$p
export https_proxy=$p

#echo $https_proxy

d=`curl -s -m 10 https://www.youtube.com/robots.txt|wc -l`

if [ $d = "0" ];
then
  echo `date +"%Y-%m-%d %T"` Proxy not working;
  cd /data/work/Anycast
  ./anycast.sh --disconnect
  sleep 5;
  ./anycast.sh --connect 12
  sleep 15;
  ./anycast.sh  --status
else
  echo `date +"%Y-%m-%d %T"` Proxy Ok;

fi