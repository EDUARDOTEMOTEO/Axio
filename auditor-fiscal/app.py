import streamlit as st
import os
import pandas as pd
import io
import zipfile
import tempfile
import requests
import plotly.express as px
API_URL = "http://127.0.0.1:8000"
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

def renderizar_tela_autenticacao():
    st.subheader("Acesso ao Sistema Axio")
    aba_login, aba_cadastro = st.tabs(["Entrar", "Cadastrar Empresa"])
    
    with aba_login:
        email = st.text_input("E-mail", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")

        if st.button("Entrar no Sistema"):
            try:
                resposta = requests.post(
                    f"{API_URL}/login",
                    data={"username": email, "password": senha},
                    timeout=3  # Evita que o Streamlit congele se a API estiver fora do ar
                )
                if resposta.status_code == 200:
                    st.session_state["token"] = resposta.json()
                    st.success("Login realizado com sucesso!")
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")
            except requests.exceptions.RequestException:
                st.error("O servidor backend não respondeu a tempo. Usa o 'Modo Demonstração' acima.")

    with aba_cadastro:
        razao_social = st.text_input("Razão Social", key="cad_razao")
        cnpj = st.text_input("CNPJ", key="cad_cnpj")
        novo_email = st.text_input("E-mail Corporativo", key="cad_email")
        nova_senha = st.text_input("Senha", type="password", key="cad_senha")
        
        if st.button("Criar Conta"):
            payload = {
                "cnpj": cnpj,
                "razao_social": razao_social,
                "email": novo_email,
                "senha": nova_senha
            }
            resposta = requests.post(f"{API_URL}/cadastrar", json=payload)
            if resposta.status_code == 200:
                st.success("Conta criada! Faça login na aba 'Entrar'.")
            else:
                st.error(resposta.json().get("detail", "Erro ao cadastrar."))

# Inicializa a base de dados ao iniciar a aplicação
init_db()


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

if "token" not in st.session_state:
    st.session_state["token"] = None

# 3. Tela de Login
def tela_login():
    st.markdown("<h2 style='text-align: center;'>⚡ Axio - Auditoria Fiscal</h2>", unsafe_allow_html=True)

# =====================================================================
# TELA DEDICADA DE AUTENTICAÇÃO (COM ACESSO DE AVALIADOR)
# =====================================================================
def tela_login():
    st.markdown("<h2 style='text-align: center;'>⚡ Axio - Auditoria Fiscal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray;'>Entre com suas credenciais, cadastre-se ou use o acesso de teste abaixo.</p>", unsafe_allow_html=True)
    
    # -----------------------------------------------------------------
    # BOTÃO DE ACESSO RÁPIDO PARA AVALIADORES / MODO DEMO
    # -----------------------------------------------------------------
    if st.button("🚀 Entrar no Modo Demonstração (Acesso Direto)", use_container_width=True, type="primary"):
        st.session_state["token"] = "demo_token_avaliador"
        st.session_state["empresa_ativa_nome"] = "Empresa Demonstração LTDA"
        st.session_state["cnpj_ativo"] = "12345678000199"
        st.success("Acessando painel em modo de teste...")
        st.rerun()

    st.markdown("---")

    aba_login, aba_cadastro = st.tabs(["🔑 Entrar no Sistema", "🏢 Cadastrar Empresa"])

    with aba_login:
        email = st.text_input("E-mail Corporativo", key="login_email")
        senha = st.text_input("Senha", type="password", key="login_senha")
        
        if st.button("Acessar Painel", use_container_width=True):
            try:
                resposta = requests.post(
                    f"{API_URL}/login",
                    data={"username": email, "password": senha}
                )
                if resposta.status_code == 200:
                    st.session_state["token"] = resposta.json()["access_token"]
                    st.success("Autenticado com sucesso!")
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")
            except Exception:
                st.error("Erro ao conectar com o servidor. Use o botão 'Modo Demonstração' acima para testar sem o backend.")

    with aba_cadastro:
        razao_social = st.text_input("Razão Social", key="cad_razao")
        cnpj = st.text_input("CNPJ (somente números)", key="cad_cnpj")
        novo_email = st.text_input("E-mail do Administrador", key="cad_email")
        nova_senha = st.text_input("Defina uma Senha", type="password", key="cad_senha")
        
        if st.button("Cadastrar e Criar Conta", use_container_width=True):
            payload = {
                "cnpj": cnpj,
                "razao_social": razao_social,
                "email": novo_email,
                "senha": nova_senha
            }
            try:
                resposta = requests.post(f"{API_URL}/cadastrar", json=payload)
                if resposta.status_code == 200:
                    st.success("Empresa e usuário cadastrados! Faça login na aba 'Entrar'.")
                else:
                    st.error(resposta.json().get("detail", "Erro ao cadastrar."))
            except Exception:
                st.error("Erro ao conectar com o servidor.")

if not st.session_state["token"]:
    tela_login()   # Exibe a tela de login
    st.stop()

# ---------------------------------------------------------------------
# GERENCIAMENTO DA EMPRESA ATIVA NA BARRA LATERAL (BUSCANDO DA API)
# ---------------------------------------------------------------------
try:
    res_lista = requests.get(f"{API_URL}/empresas/listar")
    if res_lista.status_code == 200:
        lista_empresas = res_lista.json()
    else:
        lista_empresas = []
except Exception:
    lista_empresas = []

if lista_empresas:
    # Mapeia Razão Social -> CNPJ com os dados da API
    opcoes_empresas = {emp["razao_social"]: emp["cnpj"] for emp in lista_empresas}
    
    empresa_selecionada = st.sidebar.selectbox(
        "Selecionar Empresa Ativa:", 
        options=list(opcoes_empresas.keys()),
        key="seletor_empresa_ativa"
    )
    
    cnpj_ativo = opcoes_empresas[empresa_selecionada]
    st.session_state["empresa_ativa_nome"] = empresa_selecionada
    st.session_state["cnpj_ativo"] = cnpj_ativo
    
    st.sidebar.info(f"🏢 **CNPJ Ativo:** {cnpj_ativo}")
else:
    st.sidebar.warning("Nenhuma empresa encontrada no banco da API.")
    st.session_state["cnpj_ativo"] = None

# Se estiver no modo demo e a API estiver offline, garante os dados de fallback
if st.session_state.get("token") == "demo_token_avaliador":
    try:
        res_lista = requests.get(f"{API_URL}/empresas/listar", timeout=2)
        if res_lista.status_code == 200 and res_lista.json():
            lista_empresas = res_lista.json()
        else:
            lista_empresas = [{"razao_social": "Empresa Demonstração LTDA", "cnpj": "12345678000199"}]
    except Exception:
        lista_empresas = [{"razao_social": "Empresa Demonstração LTDA", "cnpj": "12345678000199"}]
else:
    # Comportamento normal de busca via API
    try:
        res_lista = requests.get(f"{API_URL}/empresas/listar")
        lista_empresas = res_lista.json() if res_lista.status_code == 200 else []
    except Exception:
        lista_empresas = []


# 4. TRAVA DE SEGURANÇA
if not st.session_state["token"]:
    # Se não estiver logado, desenha apenas a tela de Login
    renderizar_tela_autenticacao()

else:
    # SE ESTIVER LOGADO: Adiciona botão de sair na barra lateral e libera o app
    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair (Logout)"):
        st.session_state["token"] = None
        st.rerun()

st.title("⚡ Axio - Sistema Inteligente de Auditoria Fiscal")
st.markdown("Auditoria avançada de notas fiscais, recuperação de créditos e integração contábil.")

# ---------------------------------------------------------------------
# 1. MENU LATERAL: CONEXÃO SEFAZ (CERTIFICADO A1)
# ---------------------------------------------------------------------
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

st.sidebar.markdown("---")

# ---------------------------------------------------------------------
# 2. PAINEL DE VALIDAÇÃO E EDIÇÃO DA EMPRESA ATIVA
# ---------------------------------------------------------------------
if st.session_state.get("cnpj_ativo"):
    with st.sidebar.expander("⚙️ Validar / Editar Cadastro da Empresa"):
        try:
            res_emp = requests.get(f"{API_URL}/empresa/obter/{st.session_state['cnpj_ativo']}")
            if res_emp.status_code == 200:
                dados_emp = res_emp.json()

                nova_razao = st.text_input(
                    "Razão Social", 
                    value=dados_emp.get("razao_social", ""), 
                    key="edit_razao"
                )

                regimes = ["Simples Nacional", "Lucro Presumido", "Lucro Real"]
                regime_atual = dados_emp.get("regime_tributario", "Lucro Presumido")
                idx_regime = regimes.index(regime_atual) if regime_atual in regimes else 0

                novo_regime = st.selectbox(
                    "Regime Tributário", 
                    options=regimes, 
                    index=idx_regime, 
                    key="edit_regime"
                )

                if st.button("💾 Salvar Alterações", use_container_width=True):
                    payload = {
                        "cnpj": st.session_state["cnpj_ativo"],
                        "razao_social": nova_razao,
                        "regime_tributario": novo_regime
                    }
                    res_upd = requests.put(f"{API_URL}/empresa/atualizar", json=payload)
                    
                    if res_upd.status_code == 200:
                        st.success("Dados atualizados com sucesso!")
                        st.rerun()
                    else:
                        st.error("Erro ao salvar alterações no banco.")
            else:
                st.warning("Empresa não encontrada no banco da API.")
        except Exception:
            st.error("Falha ao conectar com a API para buscar dados da empresa.")
    
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

# Na área autenticada do app.py:
st.markdown("### 📊 Histórico de Divergências no Banco de Dados")

if st.button("🔄 Carregar Histórico Acumulado"):
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    resposta = requests.get(f"{API_URL}/auditoria/historico", headers=headers)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        historico = dados.get("historico", [])
        
        if historico:
            df_historico = pd.DataFrame(historico)
            # Remove colunas técnicas e exibe tabela limpa
            df_limpo = df_historico[['data_auditoria', 'produto_nome', 'ncm', 'cfop', 'tipo_alerta', 'mensagem']]
            st.dataframe(df_limpo, use_container_width=True)
        else:
            st.info("Nenhuma divergência registrada no banco de dados para esta empresa.")
    else:
        st.error("Erro ao carregar o histórico de auditorias.")

# Área Principal de Upload (Aceita XML e PDF em simultâneo)
uploaded_files = st.file_uploader(
    "Arraste ou selecione os ficheiros (XML para Mercadorias/Peças ou PDF para NFS-e de Serviços)", 
    type=["xml", "pdf"], 
    accept_multiple_files=True
)

if uploaded_files:
    regime_ativo = "Simples Nacional"
    if st.session_state.get("cnpj_ativo"):
        try:
            res_emp = requests.get(f"{API_URL}/empresa/obter/{st.session_state['cnpj_ativo']}")
            if res_emp.status_code == 200:
                regime_ativo = res_emp.json().get("regime_tributario", "Simples Nacional")
        except Exception:
            pass

    st.info(f"⚙️ A aplicar regras de auditoria fiscal para o regime: **{regime_ativo}**")
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
                    # SUBSTITUA A LINHA DO ST.ERROR POR ESTA:
                    st.error(f"❌ Rejeitado: O ficheiro '{uploaded_file.name}' não pertence à empresa '{st.session_state.get('empresa_ativa_nome', 'ativa')}' (CNPJ Esperado: {st.session_state.get('cnpj_ativo')}).")
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
        st.info(f"💡 Nenhum histórico encontrado para a empresa selecionada ({st.session_state.get('empresa_ativa_nome', 'ativa')}). Carregue os documentos correspondentes.")

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
# ---------------------------------------------------------------------
# DASHBOARD EXECUTIVO DE INDICADORES FISCAIS (GRÁFICOS PLOTLY)
# ---------------------------------------------------------------------
st.markdown("---")
st.title("📈 Dashboard Executivo de Indicadores Fiscais")

cnpj_ativo = st.session_state.get("cnpj_ativo")

# 1. BUSCA DE HISTÓRICO (SUPORTA MODO DEMONSTRAÇÃO E API)
if st.session_state.get("token") == "demo_token_avaliador":
    dados_hist = [
        {
            "data_auditoria": "2026-10-26",
            "produto_nome": "ÓLEO LUBRIFICANTE 20W50 1L",
            "ncm": "27101911",
            "cfop": "5102",
            "tipo_alerta": "Oportunidade - Simples Nacional",
            "mensagem": "Item Monofásico (PIS/COFINS). Segregue esta receita no PGDAS-D para recuperar/evitar bi-tributação."
        },
        {
            "data_auditoria": "2026-10-26",
            "produto_nome": "PASTILHA DE FREIO BROS 160",
            "ncm": "87083090",
            "cfop": "5405",
            "tipo_alerta": "Oportunidade - Simples Nacional",
            "mensagem": "Venda de mercadoria com ICMS-ST cobrado anteriormente. Exclua do cálculo do ICMS no PGDAS-D."
        },
        {
            "data_auditoria": "2026-10-26",
            "produto_nome": "AMORTECEDOR TRASEIRO MONO",
            "ncm": "87088000",
            "cfop": "5102",
            "tipo_alerta": "Alerta - Cadastral",
            "mensagem": "NCM sem alíquota monofásica mapeada. Verificar enquadramento na tabela TIPI."
        }
    ]
else:
    try:
        headers = {"Authorization": f"Bearer {st.session_state.get('token', '')}"}
        res_hist = requests.get(
            f"{API_URL}/auditoria/historico",
            headers=headers,
            params={"cnpj": cnpj_ativo}
        )
        dados_hist = res_hist.json().get("historico", []) if res_hist.status_code == 200 else []
    except Exception:
        dados_hist = []

# 2. RENDERIZAÇÃO DOS GRÁFICOS E INDICADORES
if dados_hist:
    df_dash = pd.DataFrame(dados_hist)

    total_divergencias = len(df_dash)
    total_produtos = df_dash['produto_nome'].nunique() if 'produto_nome' in df_dash.columns else 0
    regime_exibicao = st.session_state.get("regime_ativo", "Simples Nacional")

    col_kpi1, col_kpi2, col_kpi3 = st.columns(3)
    col_kpi1.metric("Total de Apurações", total_divergencias)
    col_kpi2.metric("Produtos Com Inconsistência", total_produtos)
    col_kpi3.metric("Regime Fiscal Ativo", regime_exibicao)

    st.write("")

    col_graf1, col_graf2 = st.columns(2)

    with col_graf1:
        st.subheader("📌 Divergências por Tipo de Alerta")
        if "tipo_alerta" in df_dash.columns:
            df_tipos = df_dash['tipo_alerta'].value_counts().reset_index()
            df_tipos.columns = ['Tipo de Alerta', 'Quantidade']
            
            fig_pizza = px.pie(
                df_tipos, 
                names='Tipo de Alerta', 
                values='Quantidade',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_pizza.update_layout(margin=dict(t=20, b=20, l=10, r=10))
            st.plotly_chart(fig_pizza, use_container_width=True)

    with col_graf2:
        st.subheader("🔍 Ocorrências por CFOP")
        if "cfop" in df_dash.columns:
            df_cfop = df_dash['cfop'].value_counts().reset_index()
            df_cfop.columns = ['CFOP', 'Total']
            
            fig_bar = px.bar(
                df_cfop, 
                x='CFOP', 
                y='Total',
                text_auto=True,
                color='Total',
                color_continuous_scale='Viridis'
            )
            fig_bar.update_layout(margin=dict(t=20, b=20, l=10, r=10), showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("📋 Histórico Detalhado das Divergências")
    colunas_exibir = [col for col in ['data_auditoria', 'produto_nome', 'ncm', 'cfop', 'tipo_alerta', 'mensagem'] if col in df_dash.columns]
    st.dataframe(df_dash[colunas_exibir], use_container_width=True)

else:
    st.info(f"💡 Nenhum histórico registrado no banco para a empresa ativa ({st.session_state.get('empresa_ativa_nome', 'Selecionada')}). Execute uma auditoria para alimentar o dashboard.")

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