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
st.write("Gera **5 jogos** usando a frequência dos números e rejeitando palpites que fujam do padrão histórico (pares/ímpares, colunas e quadrantes).")

# Função auxiliar para descobrir o quadrante de um número no volante
def get_quadrante(n):
    linha = (n - 1) // 10
    coluna = (n - 1) % 10
    if linha < 3: 
        return 1 if coluna < 5 else 2
    else:         
        return 3 if coluna < 5 else 4

if st.button("🎲 Gerar 5 Palpites Inteligentes"):
    total_sorteios = frequencias['Vezes Sorteado'].sum()
    
    if total_sorteios == 0:
        pesos_normalizados = None
    else:
        pesos = frequencias['Vezes Sorteado'].values + 1
        pesos_normalizados = pesos / pesos.sum()
    
    jogos_gerados = [] # Nossa cesta de jogos válidos
    tentativas_descartadas = 0
    
    # LOOP PRINCIPAL: Continua até termos 5 jogos perfeitos
    with st.spinner("Analisando probabilidades e gerando 5 bilhetes filtrados..."):
        while len(jogos_gerados) < 5:
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
                tentativas_descartadas += 1
                continue
                
            # 3. REGRA: Colunas (Pelo menos 4 colunas diferentes)
            colunas_usadas = set((x - 1) % 10 for x in palpite_teste)
            if len(colunas_usadas) < 4:
                tentativas_descartadas += 1
                continue
                
            # 4. REGRA: Quadrantes (Pelo menos 3 quadrantes distintos)
            quadrantes_usados = set(get_quadrante(x) for x in palpite_teste)
            if len(quadrantes_usados) < 3:
                tentativas_descartadas += 1
                continue
                
            # Se passou em todas as regras, organiza os números
            palpite = list(palpite_teste)
            palpite.sort()
            
            # Verifica se esse jogo já não foi gerado nesta mesma leva (evita cartões iguais)
            if palpite not in jogos_gerados:
                jogos_gerados.append(palpite)
            else:
                tentativas_descartadas += 1

    # Quando o while terminar, significa que temos 5 jogos!
    st.balloons()
    st.success("🎯 **Seus 5 Palpites de Ouro estão prontos!**")
    
    # Exibe os 5 jogos de forma elegante em colunas ou caixas de destaque
    for i, jogo in enumerate(jogos_gerados):
        st.markdown(f"**Jogo {i+1}:** &nbsp; `{jogo[0]:02d}` - `{jogo[1]:02d}` - `{jogo[2]:02d}` - `{jogo[3]:02d}` - `{jogo[4]:02d}` - `{jogo[5]:02d}`")
        
    # Exibindo os bastidores para o usuário
    st.info(f"""
    📊 **Bastidores da Geração:**
    O algoritmo precisou criar e destruir **{tentativas_descartadas} combinações bizarras** (como 'tudo par' ou 'tudo na mesma linha') em frações de segundo para conseguir extrair esses 5 jogos estatisticamente alinhados com a história da Mega-Sena.
    """)
