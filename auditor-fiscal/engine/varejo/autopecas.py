from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="VAREJO", subgrupo="AUTOPECAS")
class AutoPecasStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        cfop = prod.get("cfop", "")
        uf_emit = kwargs.get("uf_emit", "")
        uf_dest = kwargs.get("uf_dest", "")

        # Validação de CFOP Operacional Interestadual
        if uf_emit and uf_dest and uf_emit != uf_dest and cfop.startswith("5"):
            alertas.append({
                "tipo": "Inconsistência Cadastral - CFOP Inválido",
                "impacto_estimado_rs": 0.0,
                "mensagem": f"Operação interestadual ({uf_emit} -> {uf_dest}) registrada com CFOP interno ({cfop}). Altere para o equivalente iniciado por 6."
            })

        return alertas