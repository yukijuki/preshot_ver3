#!/bin/bash
#kill server instance
pkill -f run.py
#re-do venv
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt --no-cache-dir
#run server
nohup python3 run.py &
