#!/bin/bash
## THIS SCRIPT MUST BE SUBMITTED VIA 'sbatch'
#SBATCH --job-name=isccp_timing
#SBATCH --time=04:00:00
#SBATCH --mem-per-cpu=6GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output="logs/timing-%a.log"

/home/cphillips/.conda/envs/dev/bin/python make_timing.py $SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_MAX

