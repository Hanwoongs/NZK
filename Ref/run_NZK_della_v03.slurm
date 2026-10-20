#!/bin/bash
#SBATCH --job-name=nzk_ref_v03
#SBATCH --account=jenkins
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=24
#SBATCH --mem=192G
#SBATCH --time=24:00:00
#SBATCH --output=slurm-%A.out
#SBATCH --error=slurm-%A.err
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=hk6264@princeton.edu

module purge
module load gurobi/13.0.0
module load julia/1.12.1

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

REPO="/scratch/gpfs/JENKINS/hk6264/MacroEnergy_NZK_v03"   # 0.3 — upload this folder here
CASE="$REPO/Ref"

cd "$CASE"
# 0.3 keeps Gurobi as a weakdep, so the solver lives in $REPO/run_env,
# not in the package project itself.
julia --project="$REPO/run_env" run_v1_BNEF.jl