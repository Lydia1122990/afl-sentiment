#!/bin/bash
set -e  

pip3 install -r ${SRC_PKG}/requirements.txt -t ${DEPLOY_PKG}

cp -r ${SRC_PKG}/*.py ${DEPLOY_PKG}/

cp -r ${SRC_PKG}/nltk_data ${DEPLOY_PKG}/ || true
