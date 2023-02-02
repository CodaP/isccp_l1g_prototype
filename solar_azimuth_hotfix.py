
import netCDF4
from find_files import all_files
from tqdm import tqdm

def saa_files():
    for dt, k, f in all_files():
        if k == 'solar_azimuth_angle':
            yield dt, k, f


def fix_attr(f):
    # solar_azimuth_angle:description = "solar angle for surface observer in degrees clockwise from north"
    name = 'description'
    value = 'solar angle for surface observer in degrees clockwise from east'
    nc = netCDF4.Dataset(f, 'a')
    nc.variables['solar_azimuth_angle'].setncattr(name, value)
    nc.close()

        
def main():
    with tqdm(saa_files()) as bar:
        for dt, k, f in bar:
            bar.set_description(str(dt))
            fix_attr(f)

if __name__ == '__main__':
    main()

