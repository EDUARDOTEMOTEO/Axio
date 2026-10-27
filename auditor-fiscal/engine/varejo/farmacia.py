from engine.base_strategy import BaseStrategy
from engine.registry import registrar_estrategia

@registrar_estrategia(setor="VAREJO", subgrupo="FARMACIA")
class FarmaciaStrategy(BaseStrategy):
    def auditar_item(self, prod: dict, regime_tributario: str, **kwargs) -> list:
        alertas = []
        ncm = str(prod.get("ncm", "")).strip()
        cfop = str(prod.get("cfop", "")).strip()

        # NCMs Medicamentos (3003, 3004) e Perfumaria/Higiene (3303, 3304, 3305, 3307)
        ncms_farma_monofasico = ["3003", "3004", "3303", "3304", "3305", "3307", "3401"]
        is_farma_monofasico = any(ncm.startswith(prefixo) for prefixo in ncms_farma_monofasico)

        if regime_tributario == "Simples Nacional" and is_farma_monofasico:
            if cfop in ["5102", "6102"]:
                alertas.append({
                    "tipo": "Oportunidade - PIS/COFINS Monofásico (Farmácia)",
                    "impacto_estimado_rs": float(prod.get("v_prod", 0.0)) * 0.0365,
                    "mensagem": f"Medicamento/Perfumaria NCM {ncm} possui tributação concentrada (Lei 10.147/2000). Marque a opção de PIS/COFINS Monofásico na apuração do Simples Nacional."
                })

        return alertas