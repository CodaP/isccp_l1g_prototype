#!/bin/bash
mkdir tar 2> /dev/null
tar cf tar/coord_descent.tar coord_descent/main
git archive -o tar/archive.tar HEAD
docker build -t isccp_l1g .
