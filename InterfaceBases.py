from Alvaro import Alvaro
from RepresentacaoVetorial import *
from OxAPI import *
from DesOx import DesOx
from SemEval2007 import VlddrSemEval

class InterfaceBases():
    OBJETOS = { }
    CFGS = None

    @staticmethod
    def setup(cfgs):
        CliOxAPI.CLI = CliOxAPI(cfgs)
        ExtWeb.EXT = ExtWeb(cfgs)

        BaseOx.INSTANCE = BaseOx(cfgs, CliOxAPI.CLI, ExtWeb.EXT)
        RepVetorial.INSTANCE = RepVetorial(cfgs, None, True)
        VlddrSemEval.INSTANCE = VlddrSemEval(cfgs)

        Alvaro.INSTANCE = Alvaro(cfgs, BaseOx.INSTANCE, None, RepVetorial.INSTANCE)

        dir_modelo_default = cfgs["caminho_bases"]+"/"+cfgs["modelos"]["default"]

        RepVetorial.INSTANCE.carregar_modelo(dir_modelo_default, binario=True)
        DesOx.INSTANCE = DesOx(cfgs, BaseOx.INSTANCE, RepVetorial.INSTANCE)

        InterfaceBases.CFGS = cfgs

        InterfaceBases.OBJETOS[Alvaro.__name__] = Alvaro.INSTANCE
        InterfaceBases.OBJETOS[DesOx.__name__] = DesOx.INSTANCE
        InterfaceBases.OBJETOS[BaseOx.__name__] = BaseOx.INSTANCE
        InterfaceBases.OBJETOS[CliOxAPI.__name__] = CliOxAPI.CLI
        InterfaceBases.OBJETOS[ExtWeb.__name__] = ExtWeb.EXT
        InterfaceBases.OBJETOS[RepVetorial.__name__] = RepVetorial.INSTANCE
    