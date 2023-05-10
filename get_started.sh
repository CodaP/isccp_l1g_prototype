#!/bin/bash
micromamba activate isccp
ln -s /host_dat/l1b dat/
ln -s /host_dat/docker_index dat/index
export USER=root
cd isccp_l1g/
python make_geometry.py g16 2020-07-01
python make_geometry.py g17 2020-07-01
python make_geometry.py h8 2020-07-01
python make_geometry.py m8 2020-07-01
python make_geometry.py m11 2020-07-01
python get_sorting.py g16,g17,h8,m8,m11 2020-07-01

python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 g16 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 g17 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 h8 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 m8 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 m11 temp_11_00um 2020-07-01

python make_composite.py -w dat/comp/g16_g17_h8_m11_m8/wmo_id.nc temp_11_00um 2020-07-01

