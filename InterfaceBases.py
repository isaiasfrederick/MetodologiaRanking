from Alvaro import Alvaro
from RepresentacaoVetorial import *
from OxAPI import *
from DesOx import DesOx
from SemEval2007 import VlddrSemEval
import os

class InterfaceBases():
    OBJETOS = { }
    CFGS = None
    INICIALIZADO = False

    @staticmethod
    def setup(cfgs, dir_keys=None):
        if InterfaceBases.INICIALIZADO == True:
            return

        if dir_keys != None:
            app_cfg = Util.abrir_json("./keys.json")
            cfgs['oxford']['app_id'] = app_cfg['app_id']
            cfgs['oxford']['app_key'] = app_cfg['app_key']

        Util.deletar_arquivo("../Bases/ngrams.tmp")
        Util.CONFIGS = cfgs

        CliOxAPI.CLI = CliOxAPI(cfgs)
        ExtWeb.EXT = ExtWeb(cfgs)

        BaseOx.INSTANCE = BaseOx(cfgs, CliOxAPI.CLI, ExtWeb.EXT)
        RepVetorial.INSTANCE = RepVetorial(cfgs, None, True)
        VlddrSemEval.INSTANCE = VlddrSemEval(cfgs)

        Alvaro.INSTANCE = Alvaro(cfgs, BaseOx.INSTANCE, None, RepVetorial.INSTANCE)

        dir_modelo_default = cfgs["caminho_bases"]+"/"+cfgs["modelos"]["default"]

        if cfgs['carregar_modelo'] == True:
            print("\nCarregando modelo '%s'"%dir_modelo_default)
            RepVetorial.INSTANCE.carregar_modelo(dir_modelo_default, binario=True)
            print("Modelo carregado!\n")
        else:
            RepVetorial.INSTANCE = None
            print("Modelo NAO carregado!\n")

        DesOx.INSTANCE = DesOx(cfgs, BaseOx.INSTANCE, RepVetorial.INSTANCE)

        InterfaceBases.CFGS = cfgs

        InterfaceBases.OBJETOS[Alvaro.__name__] = Alvaro.INSTANCE
        InterfaceBases.OBJETOS[DesOx.__name__] = DesOx.INSTANCE
        InterfaceBases.OBJETOS[BaseOx.__name__] = BaseOx.INSTANCE
        InterfaceBases.OBJETOS[CliOxAPI.__name__] = CliOxAPI.CLI
        InterfaceBases.OBJETOS[ExtWeb.__name__] = ExtWeb.EXT
        InterfaceBases.OBJETOS[RepVetorial.__name__] = RepVetorial.INSTANCE

        INICIALIZADO = True
    