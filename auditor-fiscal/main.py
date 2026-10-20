import os
from src.auditor import executar_auditoria
from src.reporter import gerar_relatorio_excel

def main():
    print("========================================")
    print("   Axio - Sistema de Auditoria Fiscal   ")
    print("========================================\n")
    
    # Define o caminho para a pasta de XMLs de entrada
    pasta_xmls_entrada = os.path.join("data", "xmls_entrada")
    
    # Executa a auditoria
    relatorio = executar_auditoria(pasta_xmls_entrada)
    
    # Exibe os resultados no terminal
    print("\n--- RESUMO DA AUDITORIA ---")
    if not relatorio:
        print("Nenhuma divergência ou oportunidade encontrada nos XMLs analisados.")
    else:
        print(f"Foram encontradas {len(relatorio)} ocorrências para análise.")
        for idx, item in enumerate(relatorio, 1):
            prod = item['produto']
            print(f"\n[{idx}] Produto: {prod['x_prod']} (NCM: {prod['ncm']})")
            for alerta in item['alertas']:
                print(f"    ⚠️  [{alerta['tipo']}] {alerta['mensagem']}")
                
        # Gera o relatório em Excel
        gerar_relatorio_excel(relatorio)
                
    print("\n========================================")
    print("         Processo Concluído             ")
    print("========================================")

if __name__ == "__main__":
    main()