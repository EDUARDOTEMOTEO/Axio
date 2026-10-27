from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="SAUDE", subgrupo="CLINICAS")
class ClinicasStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))
        eh_procedimento_cirurgico = prod.get("eh_procedimento", False)

        if regime_tributario == "Lucro Presumido" and v_servico > 0:
            if eh_procedimento_cirurgico:
                # Economia estimada pela redução de presunção (diferença de base de cálculo)
                economia_estimada = (v_servico * 0.24 * 0.15) + (v_servico * 0.20 * 0.09)
                alertas.append({
                    "tipo": "Oportunidade - Equiparação Hospitalar (Lei 9.249/95)",
                    "impacto_estimado_rs": round(economia_estimada, 2),
                    "mensagem": "Serviço cirúrgico/ambulatorial elegível para equiparação hospitalar. Redução da base de presunção de IRPJ (8%) e CSLL (12%)."
                })

        return alertas