"""
PAINEL DE INTELIGÊNCIA DE MERCADO E TELEMETRIA DO AXIO (painel_inteligencia.py)
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Axio - Inteligência de Mercado", layout="wide")

st.title("🧠 Axio Telemetry - Inteligência & Métricas de Mercado")
st.caption("Análise estatística do comportamento fiscal, divergências recorrentes e potencial de recuperação por perfil empresarial.")

caminho_csv = "data/telemetria_mercado_axio.csv"

if not os.path.exists(caminho_csv):
    st.warning("⚠️ O banco de telemetria ainda não foi gerado. Execute o script `python simulador_mercado_axio.py` no terminal.")
else:
    df = pd.read_csv(caminho_csv)

    # 1. MÉTRICAS MACRO
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Empresas Auditadas", df['empresa_id'].nunique())
    col2.metric("Notas Fiscalizadas", len(df))
    col3.metric("Taxa Geral de Inconsistência", f"{(df['teve_divergencia'].mean() * 100):.1f}%")
    col4.metric("Oportunidades Mapeadas (R$)", f"R$ {df['credito_recuperavel_rs'].sum():,.2f}")

    st.markdown("---")

    # 2. INSIGHTS DE MERCADO (CRUZAMENTOS E ESTATÍSTICA)
    col_g1, col_g2 = st.columns(2)

    with col_g1:
        st.subheader("📍 Taxa de Erro: Contabilidade Interna vs Terceirizada")
        df_contab = df.groupby('tipo_contabilidade')['teve_divergencia'].mean().reset_index()
        df_contab['Taxa de Erro (%)'] = df_contab['teve_divergencia'] * 100
        
        fig_contab = px.bar(
            df_contab, 
            x='tipo_contabilidade', 
            y='Taxa de Erro (%)',
            color='tipo_contabilidade',
            text_auto='.1f',
            color_discrete_map={"Interna": "#2ca02c", "Terceirizada": "#d62728"}
        )
        st.plotly_chart(fig_contab, use_container_width=True)

    with col_g2:
        st.subheader("🌎 Potencial de Crédito Recuperável por Região (R$)")
        df_regiao = df.groupby('regiao')['credito_recuperavel_rs'].sum().reset_index()
        
        fig_regiao = px.pie(
            df_regiao, 
            names='regiao', 
            values='credito_recuperavel_rs',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        st.plotly_chart(fig_regiao, use_container_width=True)

    # 3. ANÁLISE DE INCIDÊNCIA POR SEGMENTO
    st.subheader("🏬 Volume de Inconsistências por Segmento de Atuação")
    df_seg = df.groupby(['segmento', 'tipo_alerta_principal'])['nota_id'].count().reset_index()
    df_seg.columns = ['Segmento', 'Tipo de Alerta', 'Quantidade']
    
    fig_seg = px.bar(
        df_seg,
        x='Segmento',
        y='Quantidade',
        color='Tipo de Alerta',
        barmode='stack',
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    st.plotly_chart(fig_seg, use_container_width=True)

    # 4. DIAGNÓSTICO EXECUTIVO AUTOMÁTICO
    st.markdown("---")
    st.subheader("💡 Diagnóstico Preditivo de Mercado do Axio")
    
    top_segmento_erro = df[df['teve_divergencia'] == True]['segmento'].mode()[0]
    taxa_terceirizada = df[df['tipo_contabilidade'] == 'Terceirizada']['teve_divergencia'].mean() * 100
    taxa_interna = df[df['tipo_contabilidade'] == 'Interna']['teve_divergencia'].mean() * 100

    st.info(
        f"📌 **Conclusão Baseada nos Dados:** Empresas do segmento **{top_segmento_erro}** apresentam o maior volume de "
        f"falhas no aproveitamento de benefícios monofásicos. Contabilidades terceirizadas registraram uma taxa de divergência de "
        f"**{taxa_terceirizada:.1f}%**, comparadas a **{taxa_interna:.1f}%** das contabilidades internas."
    )