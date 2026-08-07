import streamlit as st
import pandas as pd
import numpy as np
from supabase import create_client, Client

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Mega-Sena Analytics", page_icon="🍀", layout="wide")

# --- CONEXÃO COM O SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("⚠️ **Erro nas credenciais:** Verifique o arquivo secrets no Streamlit.")
        st.stop()

supabase: Client = init_connection()

# --- BUSCA DADOS REAIS DO SUPABASE ---
@st.cache_data(ttl=300) # Cache de 5 minutos
def load_data():
    try:
        # Busca todas as colunas da tabela megasena ordenadas pelo concurso
        response = supabase.table("megasena").select("*").order("id", desc=False).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return pd.DataFrame()
            
        return df
    except Exception as e:
        st.error(f"Erro ao buscar dados do Supabase: {e}")
        return pd.DataFrame()

df = load_data()

# --- INTERFACE DO USUÁRIO ---
st.title("🍀 Painel Analítico da Mega-Sena")
st.markdown("Dados reais e atualizados automaticamente via **GitHub Actions + Supabase**.")

st.divider()

# VERIFICA SE EXISTEM DADOS
if df.empty:
    st.warning("⚠️ Nenhum sorteio encontrado na tabela `megasena`. Verifique se o robô do GitHub já executou ou insira os dados no Supabase.")
    st.stop()

# --- CARD DO ÚLTIMO SORTEIO REGISTRADO ---
ultimo_concurso = df.iloc[-1]

st.subheader("📌 Último Sorteio Cadastrado")
col_info, col_bolas = st.columns([1, 2])

with col_info:
    st.metric("Concurso", int(ultimo_concurso["id"]))
    st.caption(f"Data: {ultimo_concurso.get('data_sorteio', 'N/I')}")

with col_bolas:
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    b1.success(f"**{int(ultimo_concurso['bola_1']):02d}**")
    b2.success(f"**{int(ultimo_concurso['bola_2']):02d}**")
    b3.success(f"**{int(ultimo_concurso['bola_3']):02d}**")
    b4.success(f"**{int(ultimo_concurso['bola_4']):02d}**")
    b5.success(f"**{int(ultimo_concurso['bola_5']):02d}**")
    b6.success(f"**{int(ultimo_concurso['bola_6']):02d}**")

st.divider()

# --- PROCESSAMENTO E ANÁLISE DE FREQUÊNCIA ---
# Junta todas as colunas de bolas em uma única Série do Pandas
todas_as_bolas = pd.concat([
    df['bola_1'], df['bola_2'], df['bola_3'], 
    df['bola_4'], df['bola_5'], df['bola_6']
])

# Conta quantas vezes cada dezena saiu
frequencias = todas_as_bolas.value_counts().reset_index()
frequencias.columns = ['Número', 'Vezes Sorteado']

# Garante que todos os números de 1 a 60 apareçam na lista (mesmo que com 0 sorteios)
todos_numeros = pd.DataFrame({'Número': range(1, 61)})
frequencias = pd.merge(todos_numeros, frequencias, on='Número', how='left').fillna(0)
frequencias['Vezes Sorteado'] = frequencias['Vezes Sorteado'].astype(int)

# Ordenação para métricas
frequencias_ordenadas = frequencias.sort_values(by='Vezes Sorteado', ascending=False)

# --- MÉTRICAS GERAIS ---
col1, col2, col3 = st.columns(3)
col1.metric("Total de Concursos no Banco", len(df))
col2.metric("Número Mais Frequente", int(frequencias_ordenadas.iloc[0]['Número']))
col3.metric("Número Menos Frequente", int(frequencias_ordenadas.iloc[-1]['Número']))

st.divider()

# --- GRÁFICO DE FREQUÊNCIA ---
st.subheader("📊 Frequência das Dezenas")
st.bar_chart(data=frequencias.set_index('Número'))

# --- GERADOR DE PALPITES INTELIGENTE (COM FILTROS HEURÍSTICOS) ---
st.subheader("🔮 Gerador de Palpites Avançado (Filtro Histórico)")
st.write("Este algoritmo não apenas usa a frequência dos números (dando peso aos que mais saem), mas também atua como um 'fiscal', rejeitando palpites que fujam do padrão histórico (pares/ímpares, colunas e quadrantes).")

# Função auxiliar para descobrir o quadrante de um número no volante
def get_quadrante(n):
    # O volante tem 6 linhas (0 a 5) e 10 colunas (0 a 9)
    linha = (n - 1) // 10
    coluna = (n - 1) % 10
    
    if linha < 3: # Metade superior
        return 1 if coluna < 5 else 2
    else:         # Metade inferior
        return 3 if coluna < 5 else 4

if st.button("🎲 Gerar Palpite Inteligente"):
    total_sorteios = frequencias['Vezes Sorteado'].sum()
    
    if total_sorteios == 0:
        pesos_normalizados = None
    else:
        pesos = frequencias['Vezes Sorteado'].values + 1
        pesos_normalizados = pesos / pesos.sum()
    
    palpite_valido = False
    tentativas = 0
    
    # LOOP DE AMOSTRAGEM DE REJEIÇÃO
    # O Python vai gerar jogos sem parar até que um passe em todas as regras
    with st.spinner("Analisando probabilidades e aplicando filtros..."):
        while not palpite_valido and tentativas < 10000:
            tentativas += 1
            
            # 1. Gera o palpite baseado nos pesos históricos
            palpite_teste = np.random.choice(
                frequencias['Número'].values, 
                size=6, 
                replace=False, 
                p=pesos_normalizados
            )
            
            # 2. REGRA: Pares e Ímpares (Aceitamos apenas 3/3, 4/2 ou 2/4)
            pares = sum(1 for x in palpite_teste if x % 2 == 0)
            if pares not in [2, 3, 4]:
                continue # Falhou! Volta pro começo do 'while'
                
            # 3. REGRA: Colunas (Pelo menos 4 colunas diferentes)
            # Pegamos o resto da divisão por 10 para achar a coluna (ex: 15 e 25 estão na coluna 4)
            colunas_usadas = set((x - 1) % 10 for x in palpite_teste)
            if len(colunas_usadas) < 4:
                continue # Falhou!
                
            # 4. REGRA: Quadrantes (Pelo menos 3 quadrantes distintos)
            quadrantes_usados = set(get_quadrante(x) for x in palpite_teste)
            if len(quadrantes_usados) < 3:
                continue # Falhou!
                
            # Se chegou até aqui, passou em TODAS as regras do Ademir!
            palpite = palpite_teste
            palpite.sort()
            palpite_valido = True
    
    if palpite_valido:
        st.balloons()
        st.success(f"**Seu Palpite de Ouro:** {palpite[0]:02d} - {palpite[1]:02d} - {palpite[2]:02d} - {palpite[3]:02d} - {palpite[4]:02d} - {palpite[5]:02d}")
        
        # Exibindo os bastidores para o usuário
        st.info(f"""
        📊 **Relatório de Validação do Palpite:**
        - **Tentativas descartadas pelo algoritmo:** {tentativas - 1} jogos fora do padrão.
        - **Pares/Ímpares:** {pares} pares e {6-pares} ímpares.
        - **Espalhamento:** Dezenas distribuídas em {len(colunas_usadas)} colunas e {len(quadrantes_usados)} quadrantes diferentes.
        """)
    else:
        st.error("Não foi possível gerar um palpite com essas regras. Tente novamente.")
