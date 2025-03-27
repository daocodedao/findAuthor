#!/bin/bash

base_dir=/data/work/findAuthor
cd $base_dir


. colors.sh

./start_crawler_arxiv.sh
./start_crawler_teacher.sh
./start_gradio.sh