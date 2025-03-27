#!/bin/bash

base_dir=/data/work/findAuthor
cd $base_dir

jobDir=`pwd`
pythonPath=${base_dir}/venv/bin/python

. colors.sh

jobName=crawler_arxiv_paper.py
TAILPID=`ps aux | grep "$jobName" | grep -v grep | awk '{print $2}'`
echo "${YELLOW}check $jobName pid $TAILPID ${NOCOLOR}"
[ "0$TAILPID" != "0" ] && kill -9 $TAILPID


jobName=crawler_teacher.py
TAILPID=`ps aux | grep "$jobName" | grep -v grep | awk '{print $2}'`
echo "${YELLOW}check $jobName pid $TAILPID ${NOCOLOR}"
[ "0$TAILPID" != "0" ] && kill -9 $TAILPID


jobName=gradio_university.py
TAILPID=`ps aux | grep "$jobName" | grep -v grep | awk '{print $2}'`
echo "${YELLOW}check $jobName pid $TAILPID ${NOCOLOR}"
[ "0$TAILPID" != "0" ] && kill -9 $TAILPID
