#!/bin/bash
## THIS SCRIPT MUST BE SUBMITTED VIA 'sbatch'
#SBATCH --job-name=isccp_netcdf
#SBATCH --time=04:00:00
#SBATCH --mem-per-cpu=8GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output="logs/netcdf-%a.log"

export TMPDIR=/scratch/
/home/cphillips/.conda/envs/dev/bin/python rewrite_netcdfs.py --missing $SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_MAX
