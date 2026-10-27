from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="SAUDE", subgrupo="LABORATORIOS")
class LaboratoriosStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))

        if regime_tributario == "Lucro Presumido" and v_servico > 0:
            # Análises clínicas e exames possuem direito pacificado pelo STJ (Tema 217)
            economia_estimada = (v_servico * 0.24 * 0.15) + (v_servico * 0.20 * 0.09)
            alertas.append({
                "tipo": "Oportunidade - Equiparação Hospitalar Automática (STJ Tema 217)",
                "impacto_estimado_rs": round(economia_estimada, 2),
                "mensagem": "Serviços de diagnóstico e análises clínicas possuem direito pacificado à alíquota reduzida de IRPJ (8%) e CSLL (12%)."
            })

        return alertas