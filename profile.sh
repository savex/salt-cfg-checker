#!/bin/bash
python -m cProfile -o lastprofile.dat ./runtests.py
#echo -e "sort tottime\nstats 30" | python -m pstats lastprofile.dat
