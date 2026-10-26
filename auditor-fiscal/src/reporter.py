import pandas as pd
import os

def gerar_relatorio_excel(resultados, nome_arquivo="relatorio_auditoria.xlsx"):
    """
    Converte os resultados da auditoria em um DataFrame do Pandas e exporta para um arquivo Excel (.xlsx).
    """
    if not resultados:
        print("Nenhum dado de alerta para exportar no relatório.")
        return
        
    dados_formatados = []
    
    # Transforma os resultados em uma lista limpa de dicionários para a tabela
    for item in resultados:
        prod = item['produto']
        for alerta in item['alertas']:
            dados_formatados.append({
                'Chave de Acesso': prod['chave_acesso'],
                'Código': prod['c_prod'],
                'Produto': prod['x_prod'],
                'NCM': prod['ncm'],
                'Valor Unit/Total (R$)': prod['v_prod'],
                'CST PIS': prod['pis_cst'],
                'Tipo de Oportunidade': alerta['tipo'],
                'Detalhe / Mensagem': alerta['mensagem']
            })
            
    # Cria a tabela estruturada com Pandas
    df = pd.DataFrame(dados_formatados)
    
    # Salva o arquivo na raiz do projeto
    caminho_saida = os.path.join(".", nome_arquivo)
    df.to_excel(caminho_saida, index=False)
    
    print(f"\n📊 Relatório gerado com sucesso! Arquivo salvo em: {caminho_saida}")