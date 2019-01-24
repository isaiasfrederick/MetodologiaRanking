import os

pw = raw_input("Pass: ")

os.system("sshpass -p \"%s\" scp /home/isaias/PycharmProjects/MetodologiaRanking/*.py  alvaro@200.239.138.66:/home/alvaro/Isaias/MetodologiaRanking/"%pw)
os.system("sshpass -p \"%s\" scp /home/isaias/PycharmProjects/MetodologiaRanking/*.json  alvaro@200.239.138.66:/home/alvaro/Isaias/MetodologiaRanking/"%pw)
