from Alvaro import AbordagemAlvaro
from RepresentacaoVetorial import *
from OxAPI import *
from DesOx import DesOx

class InterfaceBases():
    OBJETOS = { }
    CFGS = None

    @staticmethod
    def setup(cfgs):
        CliOxAPI.CLI = CliOxAPI(cfgs)
        ExtWeb.EXT = ExtWeb(cfgs)

        BaseOx.BASE_OX = BaseOx(cfgs, CliOxAPI.CLI, ExtWeb.EXT)
        RepVetorial.REP = RepVetorial(cfgs, None, True)

        AbordagemAlvaro.ABORDAGEM = AbordagemAlvaro(cfgs, BaseOx.BASE_OX, None, RepVetorial.REP)

        dir_modelo_default = cfgs["caminho_raiz_bases"]+"/"+cfgs["modelos"]["default"]

        RepVetorial.REP.carregar_modelo(dir_modelo_default, binario=True)
        DesOx.DES = DesOx(cfgs, BaseOx.BASE_OX, RepVetorial.REP)

        InterfaceBases.CFGS = cfgs

        InterfaceBases.OBJETOS[AbordagemAlvaro.__name__] = AbordagemAlvaro.ABORDAGEM
        InterfaceBases.OBJETOS[DesOx.__name__] = DesOx.DES
        InterfaceBases.OBJETOS[BaseOx.__name__] = BaseOx.BASE_OX
        InterfaceBases.OBJETOS[CliOxAPI.__name__] = CliOxAPI.CLI
        InterfaceBases.OBJETOS[ExtWeb.__name__] = ExtWeb.EXT
        InterfaceBases.OBJETOS[RepVetorial.__name__] = RepVetorial.REP
    