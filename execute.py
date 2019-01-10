import os
import subprocess
import sys


proc = subprocess.Popen("py ./main.py "+sys.argv[1]+" >> saida.txt", stdout=subprocess.PIPE, shell=True)

print("\n\n\n")

dir(proc)

print("\n\n\n")

while True:
	pass
