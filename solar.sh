#!/bin/bash
## THIS SCRIPT MUST BE SUBMITTED VIA 'sbatch'
#SBATCH --job-name=isccp_solar
#SBATCH --time=04:00:00
#SBATCH --mem-per-cpu=8GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output="logs/solar-%a.log"

/home/cphillips/.conda/envs/dev/bin/python solar.py $SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_MAX
