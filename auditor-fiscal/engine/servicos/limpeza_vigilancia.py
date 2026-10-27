from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="SERVICOS", subgrupo="LIMPEZA_VIGILANCIA")
class LimpezaVigilanciaStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))
        inss_retido = float(prod.get("inss_retido", 0.0))

        # Cessão de mão de obra exige retenção de 11% de INSS no tomador (Art. 31 da Lei 8.212/91)
        if v_servico > 0 and inss_retido == 0.0:
            alertas.append({
                "tipo": "Alerta Fiscal - Falta de Retenção de INSS (Cessão de Mão de Obra)",
                "impacto_estimado_rs": round(v_servico * 0.11, 2),
                "mensagem": "Serviço de limpeza/vigilância sem retenção previdenciária de 11% de INSS. Risco de autuação por responsabilidade solidária do tomador."
            })

        return alertas