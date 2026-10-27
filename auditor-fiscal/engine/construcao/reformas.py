from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="CONSTRUCAO", subgrupo="REFORMAS")
class ReformasStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))
        cno = str(prod.get("cno", "")).strip()

        if v_servico > 0 and not cno:
            alertas.append({
                "tipo": "Inconsistência Cadastral - Ausência de CNO",
                "impacto_estimado_rs": 0.0,
                "mensagem": "Nota de serviço de construção/reforma sem a identificação do CNO (Cadastro Nacional de Obras). Necessário para regularização da obra perante a Receita Federal."
            })

        return alertas