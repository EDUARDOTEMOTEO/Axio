from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="SERVICOS", subgrupo="TECNOLOGIA")
class TecnologiaStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))
        doc_tomador = str(prod.get("doc_tomador", "")).strip().replace(".", "").replace("-", "").replace("/", "")
        retencoes = prod.get("retencoes", {})

        # 1. Alerta de Retenção Indevida quando o Tomador é Pessoa Física (CPF)
        if len(doc_tomador) == 11 and v_servico > 0:
            pis_cofins = float(retencoes.get("pis", 0.0)) + float(retencoes.get("cofins", 0.0))
            if pis_cofins > 0:
                alertas.append({
                    "tipo": "Alerta Cadastral - Retenção Indevida CPF",
                    "impacto_estimado_rs": round(pis_cofins, 2),
                    "mensagem": f"Retenção federal de R$ {pis_cofins:.2f} destacada para Tomador Pessoa Física. Pessoas Físicas não possuem obrigatoriedade legal de retenção na fonte (Lei nº 10.833/2003)."
                })

        return alertas