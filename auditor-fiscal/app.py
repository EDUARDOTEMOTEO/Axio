import streamlit as st
import os
import pandas as pd
import io
import zipfile
import tempfile
from src.database import salvar_registro_auditoria, obter_historico_db
from src.xml_parser import extrair_dados_xml
from src.tax_rules import auditar_produto
from src.sefaz_client import validar_certificado_a1, consultar_notas_sefaz_producao
from src.nfs_parser import extrair_dados_nfse_pdf
from src.tax_rules import auditar_produto, validar_cnpj
from src.database import (
    init_db, 
    cadastrar_empresa, 
    obter_empresas_cadastradas, 
    salvar_registro_auditoria, 
    obter_historico_db
)

# Inicializa a base de dados ao iniciar a aplicação
init_db()
with st.sidebar.expander("➕ Cadastrar Nova Empresa"):
    with st.form("form_cad_empresa"):
        novo_nome = st.text_input("Razão Social / Nome da Empresa")
        novo_cnpj = st.text_input("CNPJ (ex: 46.245.693/0001-83)")
        btn_salvar_empresa = st.form_submit_button("Guardar Empresa")
        
        if btn_salvar_empresa:
            if novo_nome and novo_cnpj:
                if validar_cnpj(novo_cnpj):
                    sucesso = cadastrar_empresa(novo_cnpj, novo_nome)
                    if sucesso:
                        st.success(f"Empresa '{novo_nome}' registada com sucesso!")
                    else:
                        st.error("Erro ao registar empresa na base de dados.")
                else:
                    st.error("❌ CNPJ inválido! Verifique os dígitos e tente novamente.")
            else:
                st.warning("Preencha todos os campos.")

df_empresas = obter_empresas_cadastradas()

if not df_empresas.empty:
    opcoes_empresas = {row['nome']: row['cnpj'] for _, row in df_empresas.iterrows()}
    nome_empresa_selecionada = st.sidebar.selectbox("Selecionar Empresa Ativa:", options=list(opcoes_empresas.keys()))
    cnpj_ativo = opcoes_empresas[nome_empresa_selecionada]
    st.sidebar.info(f"CNPJ Ativo: **{cnpj_ativo}**")
else:
    st.sidebar.warning("⚠️ Nenhuma empresa cadastrada. Utilize o botão acima para registar a primeira empresa.")
    cnpj_ativo = "00.000.000/0001-00"
    nome_empresa_selecionada = "Nenhuma Cadastrada"

# Seletor Dinâmico da Empresa Ativa com base no Banco de Dados

def converter_df_para_excel(df):
    """Converte um DataFrame para formato Excel em memória para descarregamento."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Auditoria_Axio')
    processed_data = output.getvalue()
    return processed_data

st.set_page_config(
    page_title="Axio - Auditoria Fiscal",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Axio - Sistema Inteligente de Auditoria Fiscal")
st.markdown("Auditoria avançada de notas fiscais, recuperação de créditos e integração contábil.")

# Menu Lateral para Configuração do Certificado Digital A1
st.sidebar.header("🔐 Conexão Sefaz (Certificado A1)")
modo_entrada = st.sidebar.radio("Modo de Obtenção de Notas:", ["Upload Manual de Ficheiros", "Sincronização Automática Sefaz"])

certificado_arquivo = None
senha_certificado = ""

if modo_entrada == "Sincronização Automática Sefaz":
    st.sidebar.info("Carregue o certificado digital da empresa (.pfx) para buscar as notas direto da Sefaz.")
    certificado_arquivo = st.sidebar.file_uploader("Certificado Digital (.pfx)", type=["pfx", "p12"])
    senha_certificado = st.sidebar.text_input("Senha do Certificado", type="password")
    
    if certificado_arquivo and senha_certificado:
        temp_pfx = os.path.join(".", certificado_arquivo.name)
        with open(temp_pfx, "wb") as f:
            f.write(certificado_arquivo.getbuffer())
            
        valido, dados_cert = validar_certificado_a1(temp_pfx, senha_certificado)
        if valido:
            st.sidebar.success(f"Certificado OK!\nTitular: {dados_cert['titular']}")
            cnpj_informado = st.sidebar.text_input("CNPJ da Empresa (apenas números):", value=dados_cert.get('cnpj', ''))
            nsu_alvo = st.sidebar.text_input("Consultar a partir do NSU:", value="1")
            
            if st.sidebar.button("🔄 Sincronizar Notas da Sefaz agora"):
                if cnpj_informado:
                    with st.spinner(f"A consultar Sefaz a partir do NSU {nsu_alvo}..."):
                        try:
                            sucesso, msg = consultar_notas_sefaz_producao(temp_pfx, senha_certificado, cnpj_informado, nsu_alvo)
                            if sucesso:
                                st.sidebar.success(msg)
                            else:
                                st.sidebar.error(msg)
                        except Exception as ex:
                            st.sidebar.error(f"Erro: {ex}")
                else:
                    st.sidebar.warning("Por favor, informe o CNPJ da empresa.")
        else:
            st.sidebar.error(f"Erro ao ler certificado: {dados_cert}")
            
        if os.path.exists(temp_pfx):
            os.remove(temp_pfx)

st.markdown("---")

# Área Principal de Upload (Aceita XML e PDF em simultâneo)
uploaded_files = st.file_uploader(
    "Arraste ou selecione os ficheiros (XML para Mercadorias/Peças ou PDF para NFS-e de Serviços)", 
    type=["xml", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    todos_produtos = []
    lista_servicos = []
    chaves_processadas = set()
    
    # Consulta o histórico real do banco de dados para a empresa ativa atual
    historico_db_atual = obter_historico_db(cnpj_ativo)
    if not historico_db_atual.empty and 'nome_arquivo' in historico_db_atual.columns:
        nomes_arquivos_processados = set(historico_db_atual['nome_arquivo'].values)
    else:
        nomes_arquivos_processados = set()
        
    arquivos_duplicados_avisos = []
    
    import tempfile

    for uploaded_file in uploaded_files:
        # Cria uma diretoria temporária segura para cada ficheiro
        with tempfile.TemporaryDirectory() as tmpdirname:
            temp_path = os.path.join(tmpdirname, uploaded_file.name)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            # ==========================================
            # VALIDAÇÃO CRUZADA DE CNPJ DO DOCUMENTO
            # ==========================================
            import re
            cnpj_extraido = None

            if uploaded_file.name.lower().endswith('.xml'):
                produtos = extrair_dados_xml(temp_path)
                if produtos:
                    cnpj_extraido = produtos[0].get('cnpj_emitente')
            elif uploaded_file.name.lower().endswith('.pdf'):
                dados_serv = extrair_dados_nfse_pdf(temp_path)
                if dados_serv:
                    cnpj_extraido = dados_serv.get('cnpj_prestador')

            if cnpj_extraido:
                cnpj_ativo_limpo = re.sub(r'\D', '', cnpj_ativo)
                cnpj_doc_limpo = re.sub(r'\D', '', str(cnpj_extraido))
                
                if cnpj_doc_limpo and cnpj_doc_limpo != cnpj_ativo_limpo:
                    st.error(f"❌ Rejeitado: O ficheiro '{uploaded_file.name}' pertence ao CNPJ {cnpj_extraido}, mas a empresa ativa é {nome_empresa_selecionada} ({cnpj_ativo}).")
                    continue  # Ignora este ficheiro e passa para o próximo!
            # ==========================================

            # Processamento normal...
            if uploaded_file.name.endswith('.xml'):
                if produtos:
                    chave_atual = produtos[0].get('chave_acesso')
                    if chave_atual and chave_atual not in chaves_processadas:
                        chaves_processadas.add(chave_atual)
                        todos_produtos.extend(produtos)
            elif uploaded_file.name.endswith('.pdf'):
                if dados_serv:
                    lista_servicos.append({
                        'arquivo': uploaded_file.name,
                        'dados': dados_serv
                    })
                
        if os.path.exists(temp_path):
            os.remove(temp_path)

    # Exibe avisos claros caso existam notas duplicadas barradas
    if arquivos_duplicados_avisos:
        st.warning(f"⚠️ Nota(s) duplicada(s) detetada(s) e ignorada(s) com sucesso: {', '.join(set(arquivos_duplicados_avisos))}")

    st.markdown("---")
    st.subheader("📊 Painel Geral de Resultados da Auditoria")
    
    # Processa auditoria de mercadorias (XML)
    resultados_auditoria = []
    for produto in todos_produtos:
        alertas = auditar_produto(produto)
        if alertas:
            resultados_auditoria.append({
                'produto': produto,
                'alertas': alertas
            })

    # Conta notas de serviço com irregularidades reais
    total_servicos_com_problema = sum(1 for serv in lista_servicos if serv['dados'].get('status_geral') == 'Com Irregularidade')

    # Métricas unificadas no topo
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("NF-e (Mercadorias)", len(chaves_processadas))
    col2.metric("NFS-e (Serviços)", len(lista_servicos))
    col3.metric("Irregularidades em Serviços", total_servicos_com_problema)
    col4.metric("Irregularidades em Peças", len(resultados_auditoria))

    # Exibição de Mercadorias (XML)
    if todos_produtos:
        st.markdown("### 🛠️ Auditoria de Peças e Mercadorias (NF-e - XML)")
        dados_tabela = []
        for produto in todos_produtos:
            alertas_produto = auditar_produto(produto)
            status_item = "Com Irregularidade" if alertas_produto else "Tudo OK"
            msg_alerta = alertas_produto[0]['mensagem'] if alertas_produto else "Nenhuma divergência detetada na mercadoria."
            
            dados_tabela.append({
                'Fornecedor': produto.get('nome_emitente', 'Desconhecido'),
                'CNPJ Fornecedor': produto.get('cnpj_emitente', ''),
                'Nº Nota': produto.get('numero_nota', ''),
                'Produto': produto.get('x_prod', ''),
                'NCM': produto.get('ncm', ''),
                'Valor (R$)': f"R$ {produto.get('v_prod', 0.0):.2f}",
                'Status': status_item,
                'Detalhes / Alerta': msg_alerta
            })
        df_resultado = pd.DataFrame(dados_tabela)
        st.dataframe(df_resultado, use_container_width=True)

        # Exemplo de botão de Exportação para Excel para Mercadorias (XML)
    if 'df_resultado' in locals() and not df_resultado.empty:
        st.markdown("---")
        excel_data = converter_df_para_excel(df_resultado)
        st.download_button(
            label="📥 Descarregar Relatório de Mercadorias (Excel)",
            data=excel_data,
            file_name="auditoria_pecas_axio.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Secção de Histórico Persistido (SQLite)
    st.markdown("---")
    st.markdown("### 🗄️ Histórico de Auditorias Persistidas (SQLite)")
    df_hist = obter_historico_db()
    if not df_hist.empty:
        st.dataframe(df_hist, use_container_width=True)
    else:
        st.info("Nenhum histórico registado na base de dados local ainda.")

    # Exibição de Serviços (PDF) no app.py
    if lista_servicos:
        st.markdown("### 📄 Auditoria Avançada de Notas Fiscais de Serviço (NFS-e - PDF)")
        
        dados_serv_tabela = []
        for serv in lista_servicos:
            d = serv['dados']
            dados_serv_tabela.append({
                'Ficheiro': serv['arquivo'],
                'Valor do Serviço (R$)': f"R$ {d.get('valor_servicos', 0.0):.2f}",
                'Status da Auditoria': d.get('status_geral', 'Tudo OK'),
                'Impacto Financeiro Envolvido': f"R$ {d.get('impacto_total', 0.0):.2f}"
            })
            
        df_serv = pd.DataFrame(dados_serv_tabela)
        st.dataframe(df_serv, use_container_width=True)
        
        # Secção de Inspeção Detalhada (Lupa por Nota)
        st.markdown("#### 🔍 Inspeção Detalhada por Nota de Serviço")
        nomes_ficheiros = [serv['arquivo'] for serv in lista_servicos]
        ficheiro_selecionado = st.selectbox("Selecione um ficheiro PDF para ver os detalhes e alertas completos:", nomes_ficheiros)
        
        for serv in lista_servicos:
            if serv['arquivo'] == ficheiro_selecionado:
                d = serv['dados']
                st.info(f"**Detalhes para o ficheiro:** {serv['arquivo']} | **CNPJ Prestador:** {d.get('cnpj_prestador', 'Não identificado')}")
                for idx, alerta in enumerate(d.get('alertas', []), 1):
                    st.markdown(f"* **Alerta {idx} [{alerta['tipo']}]:** {alerta['mensagem']} *(Impacto: R$ {alerta['impacto_financeiro']:.2f})*")
        
    if not resultados_auditoria and not lista_servicos:
        st.success("Nenhuma divergência ou documento pendente de análise.")
        # Executa o motor de cruzamento entre Serviços e Peças
    from src.tax_rules import auditar_cruzamento_nfse_nfe
    alertas_cruzamento = auditar_cruzamento_nfse_nfe(lista_servicos, todos_produtos)

    if alertas_cruzamento:
        st.markdown("---")
        st.markdown("### 🔄 Relatório de Cruzamento Inteligente (NFS-e vs NF-e)")
        dados_cruzamento_tabela = []
        for cruz in alertas_cruzamento:
            dados_cruzamento_tabela.append({
                'Origem da Divergência': cruz['origem'],
                'Tipo de Alerta': cruz['tipo'],
                'Parecer da Auditoria Cruzada': cruz['mensagem']
            })
        df_cruzamento = pd.DataFrame(dados_cruzamento_tabela)
        st.dataframe(df_cruzamento, use_container_width=True)
else:
    st.warning("Aguardando o carregamento dos ficheiros (XML ou PDF) para iniciar a análise.")
# ==========================================
# DASHBOARD GRÁFICO DE INDICADORES FISCAIS
# ==========================================
st.markdown("### 📈 Dashboard Executivo de Indicadores Fiscais")

col1, col2, col3 = st.columns(3)

df_hist = obter_historico_db(cnpj_ativo)

if not df_hist.empty:
    total_auditado_qtd = len(df_hist)
    total_irregularidades = len(df_hist[df_hist['status_auditoria'] != 'Tudo OK'])
    total_impacto_risco = df_hist['impacto_financeiro'].sum()
    
    col1.metric("Total de Documentos Auditados", total_auditado_qtd)
    col2.metric("Documentos com Irregularidade", total_irregularidades)
    col3.metric("Impacto Financeiro Total na Mesa", f"R$ {total_impacto_risco:.2f}")
    
    st.markdown("#### 📊 Distribuição de Status das Auditorias")
    status_counts = df_hist['status_auditoria'].value_counts()
    st.bar_chart(status_counts)
else:
    col1.metric("Total de Documentos Auditados", 0)
    col2.metric("Documentos com Irregularidade", 0)
    col3.metric("Impacto Financeiro Total na Mesa", "R$ 0.00")
    st.info(f"💡 Nenhum histórico encontrado para a empresa selecionada ({nome_empresa_selecionada}). Carregue os documentos correspondentes.")

    # Opção de Upload de Ficheiro ZIP em Lote
st.sidebar.markdown("---")
arquivo_zip = st.sidebar.file_uploader("📦 Carregar Lote em ZIP (XMLs/PDFs)", type=["zip"])

if arquivo_zip is not None:
    with tempfile.TemporaryDirectory() as tmpdirname:
        # Extrai o ZIP para uma pasta temporária
        with zipfile.ZipFile(arquivo_zip, 'r') as zip_ref:
            zip_ref.extractall(tmpdirname)
        
        # Lista todos os ficheiros extraídos recursivamente
        caminhos_encontrados = []
        for root, dirs, files in os.walk(tmpdirname):
            for file in files:
                caminhos_encontrados.append(os.path.join(root, file))
        
        xmls_lote = [f for f in caminhos_encontrados if f.lower().endswith('.xml')]
        pdfs_lote = [f for f in caminhos_encontrados if f.lower().endswith('.pdf')]
        
        st.success(f"Lote desomprimido com sucesso! Encontrados: {len(xmls_lote)} XML(s) e {len(pdfs_lote)} PDF(s).")
        
        # Processamento automático dos XMLs do lote
        todos_produtos_lote = []
        for xml_path in xmls_lote:
            produtos_xml = extrair_dados_xml(xml_path)
            for prod in produtos_xml:
                alertas_prod = auditar_produto(prod)
                status_prod = "Com Irregularidade" if alertas_prod else "Tudo OK"
                impacto_prod = sum(a['impacto_financeiro'] for a in alertas_prod)
                
                # Regista na base de dados SQLite
                salvar_registro_auditoria("XML (Lote)", os.path.basename(xml_path), status_prod, impacto_prod)
                
                todos_produtos_lote.append({
                    'Fornecedor': prod['nome_emitente'],
                    'CNPJ Fornecedor': prod['cnpj_emitente'],
                    'Nº Nota': prod['numero_nota'],
                    'Produto': prod['x_prod'],
                    'NCM': prod['ncm'],
                    'Valor (R$)': f"R$ {prod['v_prod']:.2f}",
                    'Status': status_prod,
                    'Detalhes / Alerta': alertas_prod[0]['mensagem'] if alertas_prod else "Nenhuma divergência detetada."
                })
        
        if todos_produtos_lote:
            st.markdown("### 📊 Resultado do Lote de Mercadorias (XML)")
            st.dataframe(pd.DataFrame(todos_produtos_lote), use_container_width=True)

        # Processamento automático dos PDFs do lote
        lista_servicos_lote = []
        for pdf_path in pdfs_lote:
            nome_arq = os.path.basename(pdf_path)
            dados_pdf = extrair_dados_nfse_pdf(pdf_path)
            
            salvar_registro_auditoria("PDF (Lote)", nome_arq, dados_pdf['status_geral'], dados_pdf['impacto_total'])
            
            lista_servicos_lote.append({
                'arquivo': nome_arq,
                'dados': dados_pdf
            })
            
        if lista_servicos_lote:
            st.markdown("### 📄 Resultado do Lote de Serviços (PDF)")
            tabela_serv_lote = []
            for serv in lista_servicos_lote:
                d = serv['dados']
                tabela_serv_lote.append({
                    'Ficheiro': serv['arquivo'],
                    'Valor do Serviço (R$)': f"R$ {d.get('valor_servicos', 0.0):.2f}",
                    'Status da Auditoria': d.get('status_geral', 'Tudo OK'),
                    'Impacto Financeiro Envolvido': f"R$ {d.get('impacto_total', 0.0):.2f}"
                })
            st.dataframe(pd.DataFrame(tabela_serv_lote), use_container_width=True)