#!/bin/bash
mkdir tar 2> /dev/null
tar cf tar/coord_descent.tar coord_descent/main
git archive -o tar/archive.tar HEAD
podman build --format docker -t isccp_l1g .
