from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="CONSTRUCAO", subgrupo="EMPREITEIRAS")
class EmpreiteirasStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        v_servico = float(prod.get("v_prod", 0.0) or prod.get("valor_servicos", 0.0))
        v_materiais = float(prod.get("v_materiais", 0.0))
        inss_retido = float(prod.get("inss_retido", 0.0))

        # 1. Abatimento de Materiais Próprios/Fornecidos na base do ISS
        if v_servico > 0 and v_materiais > 0:
            economia_iss = v_materiais * 0.05  # Estimativa com alíquota de 5% de ISS
            alertas.append({
                "tipo": "Oportunidade - Abatimento de Materiais no ISS (RE 603.497/STF)",
                "impacto_estimado_rs": round(economia_iss, 2),
                "mensagem": f"Materiais empregados (R$ {v_materiais:.2f}) podem ser deduzidos da base de cálculo do ISS, gerando uma economia estimada de R$ {economia_iss:.2f}."
            })

        # 2. Ausência de Retenção Obrigatória de INSS (11% ou 3,5%)
        if v_servico > 0 and inss_retido == 0.0 and prod.get("tem_mao_de_obra", False):
            alertas.append({
                "tipo": "Alerta Fiscal - Ausência de Retenção de INSS (11%)",
                "impacto_estimado_rs": round(v_servico * 0.11, 2),
                "mensagem": "Serviço de empreitada sem o destaque da retenção previdenciária de INSS (Art. 31 da Lei 8.212/91)."
            })

        return alertas