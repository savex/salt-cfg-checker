#!/bin/bash
#python -m cProfile -o lastprofile.dat ./tests/runtests.py
echo -e "sort tottime\nstats 50" | python -m pstats lastprofile.dat
