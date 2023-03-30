import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path
from make_composite import netcdf_path
from tqdm import tqdm
import PIL
from contextlib import contextmanager
import os
import subprocess

PLOT_DATA = {
    'solar_zenith_angle': {
        'cmap': 'viridis',
        'vmin': 0,
        'vmax': 180,
        'title': 'Solar Zenith Angle',
    },
    'solar_azimuth_angle': {
        'cmap': 'twilight',
        'vmin': -180,
        'vmax': 180,
        'title': 'Solar Azimuth Angle',
    },
    'satellite_zenith_angle': {
        'cmap': 'viridis',
        'vmin': 0,
        'vmax': 90,
        'title': 'Satellite Zenith Angle',
    },
    'satellite_azimuth_angle': {
        'cmap': 'twilight',
        'vmin': -180,
        'vmax': 180,
        'title': 'Satellite Azimuth Angle',
    },
    'temp_11_00um': {
        'cmap': 'viridis',
        'vmin': 200,
        'vmax': 300,
        'title': '11µm Brightness Temperature',
    },
    'temp_13_30um': {
        'cmap': 'viridis',
        'vmin': 200,
        'vmax': 300,
        'title': '13.3µm Brightness Temperature',
    },
    'refl_00_65um': {
        'cmap': 'viridis',
        'vmin': 0,
        'vmax': 100,
        'title': '0.65µm Reflectance',
    },
    'refl_00_86um': {
        'cmap': 'viridis',
        'vmin': 0,
        'vmax': 100,
        'title': '0.86µm Reflectance',
    },
    'refl_01_60um': {
        'cmap': 'viridis',
        'vmin': 0,
        'vmax': 100,
        'title': '1.6µm Reflectance',
    },
    'temp_03_80um': {
        'cmap': 'viridis',
        'vmin': 200,
        'vmax': 300,
        'title': '3.8µm Brightness Temperature',
    },
    'temp_07_30um': {
        'cmap': 'viridis',
        'vmin': 200,
        'vmax': 300,
        'title': '7.3µm Brightness Temperature',
    },
}

def render_fast(fig, out_fp):
    canvas = fig.canvas
    im = PIL.Image.fromarray(np.asarray(fig.canvas.buffer_rgba()))
    width, height = im.size
    width -= width % 8
    height -= height % 8
    im = im.resize((width,height))
    im.save(out_fp, format='png')
    out_fp.flush()


@contextmanager
def make_video(out='output.mkv', framerate=10, debug=False, ffmpeg='ffmpeg', bitrate="4000k"):
    out = Path(out).absolute()
    if out.is_file():
        out.unlink()

    #palette = Path('palette.png').absolute()
    palette = out.parent / f'{out.stem}_palette.png'
    #tmp = Path('tmp.mkv').absolute()
    tmp = out.parent / f'{out.stem}_tmp.mkv'
    if tmp.is_file():
        tmp.unlink()
    if palette.is_file():
        palette.unlink()
    args_mk_video = [ffmpeg,"-framerate",f"{framerate}",
            "-f","image2pipe","-i","-","-b:v",bitrate, "-pix_fmt","yuv420p", str(tmp)]
    args_palettegen = [ffmpeg, "-i",str(tmp),'-filter_complex','[0:v] palettegen',str(palette)]
    args_mk_gif = [ffmpeg,
            "-i",str(tmp),
            "-i",str(palette),'-filter_complex', '[0:v][1:v] paletteuse',
             str(out)]
    if debug:
        print(' '.join(args_mk_video))
        p = subprocess.Popen(args_mk_video, stdin=subprocess.PIPE)
    else:
        p = subprocess.Popen(args_mk_video, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        yield p.stdin
    finally:
        p.stdin.close()
        p.wait()
    if debug:
        print(' '.join(args_palettegen))
        p = subprocess.Popen(args_palettegen)
        p.wait()
        print(' '.join(args_mk_gif))
        p = subprocess.Popen(args_mk_gif)
        p.wait()
    else:
        p = subprocess.Popen(args_palettegen, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait()
        p = subprocess.Popen(args_mk_gif, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.wait()
        if palette.is_file():
            palette.unlink()
        if tmp.is_file():
            tmp.unlink()

def main(variable, dts, outdir):
    start_dt = dts[0]
    end_dt = dts[-1]
    video_f = outdir / f'{variable}_{start_dt.strftime("%Y%m%d%H%M")}_{end_dt.strftime("%Y%m%d%H%M")}.mkv'
    with make_video(out=video_f, framerate=30) as fp:
        with tqdm(dts) as bar:
            for dt in bar:
                f = netcdf_path(variable, dt)
                if f.is_file():
                    ds = xr.open_dataset(f)
                    if len(ds[variable].shape) == 3:
                        v = ds[variable][0].values[::10,::10]
                    elif len(ds[variable].shape) == 4:
                        v = ds[variable][0, 0].values[::10,::10]
                else:
                    v = np.ma.masked_all((360,720), dtype=np.float32)
                fig = plt.figure(figsize=(8, 4), facecolor='w', dpi=100)
                ax = plt.Axes(fig, [0.05, 0.07, 1.0, .85])
                fig.add_axes(ax)
                plot_data = PLOT_DATA[variable]
                cm = ax.imshow(v, cmap=plot_data['cmap'], vmin=plot_data['vmin'],
                   vmax=plot_data['vmax'], extent=[-180, 180, -90, 90], aspect='auto')
                ds.close()
                fig.colorbar(cm, ax=ax, shrink=0.5)
                title_part = plot_data['title']
                ax.set_title(dt.strftime(f'%Y-%m-%d %H:%M {title_part}'))
                if not f.is_file():
                    ax.text(0.5, 0.5, 'No data', horizontalalignment='center',
                        verticalalignment='center', transform=ax.transAxes)
                plt.draw_all()
                render_fast(fig, fp)
                plt.close(fig)

    print(f'Wrote {video_f}')
            
            

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-o', '--outdir', default='.')
    parser.add_argument('variable')
    parser.add_argument('start_dt')
    parser.add_argument('end_dt')
    parser.add_argument('--freq', default='30min')
    args = parser.parse_args()
    start_dt = pd.to_datetime(args.start_dt)
    end_dt = pd.to_datetime(args.end_dt)
    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True)
    dts = pd.date_range(start_dt, end_dt, freq=args.freq)
    main(args.variable, dts, outdir)
