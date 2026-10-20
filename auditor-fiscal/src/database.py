import sqlite3
import pandas as pd
from datetime import datetime

def init_db():
    """Inicializa a base de dados SQLite local com tabelas de empresas e histórico."""
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    
    # Tabela de Empresas Cadastradas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS empresas (
            cnpj TEXT PRIMARY KEY,
            nome TEXT NOT NULL,
            data_cadastro TEXT
        )
    ''')
    
    # Tabela de Histórico de Auditorias vinculada às empresas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS historico_auditorias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            cnpj_empresa TEXT,
            tipo_documento TEXT,
            nome_arquivo TEXT,
            status_auditoria TEXT,
            impacto_financeiro REAL,
            UNIQUE(cnpj_empresa, nome_arquivo),
            FOREIGN KEY(cnpj_empresa) REFERENCES empresas(cnpj)
        )
    ''')
    
    conn.commit()
    conn.close()

def cadastrar_empresa(cnpj, nome):
    """Regista uma nova empresa na base de dados."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO empresas (cnpj, nome, data_cadastro)
            VALUES (?, ?, ?)
        ''', (cnpj, nome, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        conn.commit()
        return True
    except Exception as e:
        return False
    finally:
        conn.close()

def obter_empresas_cadastradas():
    """Retorna todas as empresas cadastradas em formato DataFrame."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    df = pd.read_sql('SELECT * FROM empresas ORDER BY nome', conn)
    conn.close()
    return df

def salvar_registro_auditoria(cnpj_empresa, tipo_doc, nome_arquivo, status, impacto):
    """Regista ou atualiza uma auditoria associada a um CNPJ específico."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO historico_auditorias (data_hora, cnpj_empresa, tipo_documento, nome_arquivo, status_auditoria, impacto_financeiro)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(cnpj_empresa, nome_arquivo) DO UPDATE SET
            data_hora = excluded.data_hora,
            tipo_documento = excluded.tipo_documento,
            status_auditoria = excluded.status_auditoria,
            impacto_financeiro = excluded.impacto_financeiro
    ''', (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), cnpj_empresa, tipo_doc, nome_arquivo, status, impacto))
    conn.commit()
    conn.close()
    

def obter_historico_db(cnpj_empresa=None):
    """Retorna o histórico de auditorias filtrado pelo CNPJ da empresa ativa."""
    init_db()
    conn = sqlite3.connect('auditorias_axio.db')
    if cnpj_empresa:
        df = pd.read_sql('SELECT * FROM historico_auditorias WHERE cnpj_empresa = ? ORDER BY id DESC', conn, params=(cnpj_empresa,))
    else:
        df = pd.read_sql('SELECT * FROM historico_auditorias ORDER BY id DESC', conn)
    conn.close()
    return df