import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client
from collections import Counter

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mega-Sena Analytics", page_icon="🍀", layout="wide")

# --- CONEXÃO COM O SUPABASE ---
# Lembre-se de colocar suas credenciais no arquivo .streamlit/secrets.toml
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- BUSCA DE DADOS ---
@st.cache_data(ttl=600) # Cache para não sobrecarregar o Supabase
def load_data():
    # Na vida real, você puxaria da sua tabela: 
    # response = supabase.table("megasena").select("*").execute()
    # df = pd.DataFrame(response.data)
    
    # PARA TESTE IMEDIATO (Mock Data): Gerando 100 sorteios aleatórios
    # Substitua este bloco pelo código acima quando sua tabela estiver pronta
    np.random.seed(42)
    dados_mock = {
        "concurso": range(1, 101),
        "bola_1": np.random.randint(1, 61, 100),
        "bola_2": np.random.randint(1, 61, 100),
        "bola_3": np.random.randint(1, 61, 100),
        "bola_4": np.random.randint(1, 61, 100),
        "bola_5": np.random.randint(1, 61, 100),
        "bola_6": np.random.randint(1, 61, 100),
    }
    return pd.DataFrame(dados_mock)

df = load_data()

# --- INTERFACE DO USUÁRIO ---
st.title("🍀 Painel Analítico da Mega-Sena")
st.markdown("Bem-vindo ao laboratório de estudos de Python! Analisando frequências históricas.")

st.divider()

# --- PROCESSAMENTO DE DADOS (PANDAS) ---
# Juntando todas as bolas em uma única lista para contar a frequência
todas_as_bolas = pd.concat([df['bola_1'], df['bola_2'], df['bola_3'], df['bola_4'], df['bola_5'], df['bola_6']])
frequencias = todas_as_bolas.value_counts().reset_index()
frequencias.columns = ['Número', 'Vezes Sorteado']
frequencias = frequencias.sort_values(by='Vezes Sorteado', ascending=False)

# --- MÉTRICAS GERAIS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total de Sorteios Analisados", len(df))
col2.metric("Número Mais Frequente (Quente)", int(frequencias.iloc[0]['Número']))
col3.metric("Número Menos Frequente (Frio)", int(frequencias.iloc[-1]['Número']))

# --- VISUALIZAÇÕES ---
st.subheader("📊 Frequência dos Números (Gráfico)")
# Streamlit tem gráficos nativos fáceis de usar
st.bar_chart(data=frequencias.set_index('Número'))

st.subheader("🔮 Gerador de Palpites Baseado em Frequência")
st.write("Gere um jogo aleatório, mas dando *peso* maior aos números que mais saíram (Estatística Bayesiana simples).")

if st.button("Gerar Palpite Inteligente"):
    # Probabilidade baseada na frequência histórica
    pesos = frequencias.sort_values(by='Número')['Vezes Sorteado'].values
    pesos_normalizados = pesos / pesos.sum()
    
    # Escolhe 6 números sem repetição, usando os pesos
    palpite = np.random.choice(
        frequencias.sort_values(by='Número')['Número'].values, 
        size=6, 
        replace=False, 
        p=pesos_normalizados
    )
    palpite.sort()
    
    st.success(f"Seus números da sorte: **{palpite[0]} - {palpite[1]} - {palpite[2]} - {palpite[3]} - {palpite[4]} - {palpite[5]}**")
