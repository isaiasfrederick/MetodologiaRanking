import requests
import glob
import json
import os

class Utilitarios(object):
    @staticmethod
    def requisicao_http(url, headers=None):
        if headers:
            res = requests.get(url, headers = headers)
        else:
            res = requests.get(url)

        return res if res.status_code == 200 else None

    @staticmethod
    def multipalavra(palavra):
        return '-' in palavra or ' ' in palavra or '_' in palavra

    @staticmethod
    def remover_multipalavras(lista):
        return [e for e in lista if Utilitarios.multipalavra(e) == False]

    @staticmethod
    def carregar_configuracoes(dir_configs):
        arq = open(dir_configs, 'r')
        obj = json.loads(arq.read())
        arq.close()
        
        return obj

    @staticmethod
    def cosseno(conjunto1, conjunto2):
        return ""

    @staticmethod
    def carregar_json(diretorio):
        try:
            arq = open(diretorio, 'r')
            obj = json.loads(arq.read())
            arq.close()

            return obj

        except:
            return None

    @staticmethod
    def deletar_arquivo(dir_arquivo):
        system("rm " + dir_arquivo)

    @staticmethod
    def limpar_diretorio_temporarios(configs):
        os.system('rm ' + configs['dir_temporarios'] + '/*')

    @staticmethod
    def salvar_json(diretorio, obj):
        try:
            arq = open(diretorio, 'w')
            obj_serializado = json.dumps(obj, indent=4)
            arq.write(obj_serializado)
            arq.close()

            return True
        except:
            return False

    @staticmethod
    def listar_arquivos(diretorio):
        return glob.glob(diretorio + '/*')