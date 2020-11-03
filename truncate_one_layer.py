import netCDF4
import io

def main(path_in, path_out):
    with open(path_in,'rb') as fp:
        nc_in = netCDF4.Dataset("memory", memory=fp.read(), mode='r')
    nc_out = netCDF4.Dataset(path_out, mode='w')
    for k,v in nc_in.dimensions.items():
        if k == 'layer':
            nc_out.createDimension(k,1)
        else:
            nc_out.createDimension(k,v.size)

    for k,v in nc_in.variables.items():
        dims = v.dimensions
        nc_out.createVariable(k, v.dtype, dims, zlib=True, fill_value=v._FillValue, chunksizes=v.chunking())
    for k,v in nc_in.variables.items():
        dims = v.dimensions
        if 'layer' in dims:
            slices = tuple(slice(None) if k != 'layer' else slice(0,1) for k in dims)
            data = v[slices]
        else:
            data = v[:]
        for attr in v.ncattrs():
            if attr in ['_FillValue']:
                continue
            nc_out.variables[k].setncattr(attr, v.getncattr(attr))
        nc_out.variables[k][:] = data

    for attr in nc_in.ncattrs():
        nc_out.setncattr(attr, nc_in.getncattr(attr))

    nc_out.close()
    nc_in.close()


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('src')
    parser.add_argument('dst')
    args = parser.parse_args()
    main(args.src, args.dst)
