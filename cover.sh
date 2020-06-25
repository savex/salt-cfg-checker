#!/bin/bash
PYTHONPATH=. coverage run --source=cfg_checker ./runtests.py
coverage xml && coverage report
