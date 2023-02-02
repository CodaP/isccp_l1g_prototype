#!/bin/bash
## THIS SCRIPT MUST BE SUBMITTED VIA 'sbatch'
#SBATCH --job-name=unshuffle
#SBATCH --time=02:00:00
#SBATCH --mem-per-cpu=8GB
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --output="logs/unshuffle-%a.log"

python unshuffle.py $SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_MAX
