from pathlib import Path
import netCDF4

def get_sample(k):
    return next(Path('dat/final/2020/07/01/0000/').glob(f'*__{k}__*'))



def test_satazi():
    k = 'satellite_azimuth_angle'
    f = get_sample(k)
    nc = netCDF4.Dataset(f)
    attrs = nc.variables[k].__dict__
    assert attrs['description'] == 'satellite angle for surface observer in degrees clockwise from north'
    assert attrs['value_range'] == '-180 to 180 degrees'
    nc.close()

def test_solazi():
    k = 'solar_azimuth_angle'
    f = get_sample(k)
    nc = netCDF4.Dataset(f)
    attrs = nc.variables[k].__dict__
    assert attrs['description'] == 'solar angle for surface observer in degrees clockwise from north'
    assert attrs['value_range'] == '-180 to 180 degrees'
    nc.close()


