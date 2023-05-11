#!/bin/bash
micromamba activate isccp
cd dat/
tar xvf /host/tar/example_l1b.tar.gz
ln -s /host/dat/index .
export USER=root
cd ../
cd isccp_l1g/

############
# Initialize
python make_index.py 2020-07-01
python make_geometry.py g16 2020-07-01
python make_geometry.py g17 2020-07-01
python make_geometry.py h8 2020-07-01
python make_geometry.py m8 2020-07-01
python make_geometry.py m11 2020-07-01
python get_sorting.py g16,g17,h8,m8,m11 2020-07-01
############

# resample the l1b data
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 g16 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 g17 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 h8 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 m8 temp_11_00um 2020-07-01
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 m11 temp_11_00um 2020-07-01

# compute the pixel times
python make_timing.py --compdir dat/comp/g16_g17_h8_m11_m8/ g16 2020-07-01
python make_timing.py --compdir dat/comp/g16_g17_h8_m11_m8/ g17 2020-07-01
python make_timing.py --compdir dat/comp/g16_g17_h8_m11_m8/ h8 2020-07-01
python make_timing.py --compdir dat/comp/g16_g17_h8_m11_m8/ m8 2020-07-01
python make_timing.py --compdir dat/comp/g16_g17_h8_m11_m8/ m11 2020-07-01

# composite
python make_composite.py -w dat/comp/g16_g17_h8_m11_m8/wmo_id.nc temp_11_00um 2020-07-01
python make_composite.py -w dat/comp/g16_g17_h8_m11_m8/wmo_id.nc pixel_time 2020-07-01

# copy wmo_id and sample_mode to timestep
python make_ancil.py --compdir dat/comp/g16_g17_h8_m11_m8/ 2020-07-01

# make solar zenith and azimuth
python make_solar.py 2020-07-01


