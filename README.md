# ISCCP L1g Prototype

The ISCCP Level-1G (L1G) dataset is a composition of imagery from all advanced geostationary imagers into homogeneous and globally gridded fields.
Sensor overlap is handled using a layering scheme similar to that of the NOAA/NESDIS GridSat product.
The L1G is intended to be the input for ISCCP-NG L2, but can also be a resource for applications needing geostationary data.
The provisional approach is to include all channels every 30 minutes with a maximum resolution of 4 km on a Equirectangular grid.

## Processing Outline

![Processing Outline](docs/l1g_processing_diagram.png)

* By default directories (`l1b/`,`index/`,`final/`, etc) are created under `dat/`, make this a symlink to a larger storage area if needed.
* shorthand for each satellite is defined in `utils.py` (e.g. `g16`, `h8`, `m11`, etc)

### Steps

#### Construct Index

The first step is to construct the resampling index for each satellite.
To do this we need at least one granule of data to provide the coordinates of the satellite pixels.
We assume the data is fix-grid. This step only needs to be done once for each resolution of each sensor.

*Example:*
```
# Try to create an index for every satellite in utils.py:ALL_SATS
python make_index.py 2020-07-01
...
ls dat/index/g16/refl_00_47um/
    dst_index.dat  src_index.dat dst_index_nn.dat  src_index_nn.dat
```

#### Make Geometry

This step makes the satellite zenith and azimuth angles for each pixel in the final grid.
It is expected that these can change so it should be run every timestep.
The zenith angle is compared between satellites to decide which layer to put the pixel in.
That sorting is intended to be fixed over long periods of time. So run it at least once on a representative timestep.

*Example:*
```
python make_geometry.py g16 2020-07-01
...
ls dat/sample_cache/2020/07/01/0000/g16/
    satellite_azimuth_angle.dat.zstd  satellite_zenith_angle.dat.zstd
```

#### Freeze Sorting

This step determines how many layers are needed in the output and which satellite goes in each layer as well as when the sampling mode is averaged or nearest-neighbor.
This depends on the satellite composition.
It is expected that this will be fixed over long periods of time, so it should be run once on a representative timestep.

*Example:*
```
python get_sorting.py g16,g17,h8,m8,m11 2020-07-01
...
ls dat/comp/g16_g17_h8_m11_m8/
    sample_mode.nc  wmo_id.nc
```

#### Resampling Data

This step reads L1b data for one band of one satellite and resamples it to the final grid and then saves it to disk in an intermediate format. This intermediate format is very similar to the final netcdf format.
Floating point data is converted into packed-integers and compressed.
The `temp_11_00um` and `refl_00_65um` bands are special in that statistics are computed for them.

*Example:*
```
python make_sample.py --compdir dat/comp/g16_g17_h8_m11_m8 g16 temp_11_00um 2020-07-01
...
ls dat/sample_cache/2020/07/01/0000/g16/
    temp_11_00um.dat.zstd
    temp_11_00um_count.dat.zstd
    temp_11_00um_max.dat.zstd
    temp_11_00um_min.dat.zstd
    temp_11_00um_std.dat.zstd
```


#### Composite

This step reads the intermediate files and shuffles the data into the final netcdf format.

*Example:*
```
python make_composite.py -w dat/comp/g16_g17_h8_m11_m8/wmo_id.nc temp_11_00um 2020-07-01
...
ls dat/final/2020/07/01/0000/
    ISCCP-NG_L1g_demo_v2_res_0_05deg__temp_11_00um__20200701T0000.nc
```


### L1b

* The level 1b data should be organized into the following directory structure:
```
YYYY/
  MM/
    DD/
      HHMM/
        $SAT/
          $BAND/
            <files>
```
* So far only GOES ABI `.nc`, AHI `.dat`, and MSG HRIT files have been tested, but any format that can be read by `satpy` should work with some modifications to the `utils.py` file.
* List of bands
    - refl_00_47um
    - refl_00_51um
    - refl_00_65um
    - refl_00_86um
    - refl_01_38um
    - refl_01_60um
    - refl_02_20um
    - temp_03_80um
    - temp_06_20um
    - temp_06_70um
    - temp_07_30um
    - temp_08_60um
    - temp_09_70um
    - temp_10_40um
    - temp_11_00um
    - temp_12_00um
    - temp_13_30um

