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
        st.error("⚠️ Erro nas credenciais.")
        st.stop()

supabase: Client = init_connection()

# --- BUSCA DE DADOS ---
@st.cache_data(ttl=300)
def load_data():
    response = supabase.table("megasena").select("*").order("id", desc=False).execute()
    return pd.DataFrame(response.data)

def buscar_meus_jogos():
    response = supabase.table("meus_jogos").select("*").order("id", desc=True).execute()
    return pd.DataFrame(response.data)

df = load_data()
if df.empty:
    st.warning("Nenhum sorteio encontrado no banco oficial.")
    st.stop()

ultimo_concurso = df.iloc[-1]
proximo_concurso_previsto = int(ultimo_concurso['id']) + 1

st.title("🍀 Painel Analítico da Mega-Sena")
st.markdown(f"**Último Concurso Registrado:** {int(ultimo_concurso['id'])} (Data: {ultimo_concurso.get('data_sorteio', 'N/I')})")
st.divider()

# --- CRIANDO ABAS DE NAVEGAÇÃO ---
aba_dash, aba_gerador, aba_conferidor = st.tabs(["📊 Dashboard Histórico", "🔮 Gerador Inteligente", "✅ Conferidor de Jogos"])

# ==========================================
# ABA 1: DASHBOARD
# ==========================================
with aba_dash:
    st.subheader(f"📌 Dezenas Sorteadas no Concurso {int(ultimo_concurso['id'])}")
    b1, b2, b3, b4, b5, b6 = st.columns(6)
    b1.success(f"**{int(ultimo_concurso['bola_1']):02d}**")
    b2.success(f"**{int(ultimo_concurso['bola_2']):02d}**")
    b3.success(f"**{int(ultimo_concurso['bola_3']):02d}**")
    b4.success(f"**{int(ultimo_concurso['bola_4']):02d}**")
    b5.success(f"**{int(ultimo_concurso['bola_5']):02d}**")
    b6.success(f"**{int(ultimo_concurso['bola_6']):02d}**")

    todas_as_bolas = pd.concat([df['bola_1'], df['bola_2'], df['bola_3'], df['bola_4'], df['bola_5'], df['bola_6']])
    frequencias = todas_as_bolas.value_counts().reset_index()
    frequencias.columns = ['Número', 'Vezes Sorteado']
    todos_numeros = pd.DataFrame({'Número': range(1, 61)})
    frequencias = pd.merge(todos_numeros, frequencias, on='Número', how='left').fillna(0)
    frequencias['Vezes Sorteado'] = frequencias['Vezes Sorteado'].astype(int)
    frequencias_ordenadas = frequencias.sort_values(by='Vezes Sorteado', ascending=False)

    st.divider()
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Concursos Analisados", len(df))
    col2.metric("Número Mais Frequente", int(frequencias_ordenadas.iloc[0]['Número']))
    col3.metric("Número Menos Frequente", int(frequencias_ordenadas.iloc[-1]['Número']))

    st.subheader("📊 Frequência das Dezenas")
    st.bar_chart(data=frequencias.set_index('Número'))

# ==========================================
# ABA 2: GERADOR
# ==========================================
with aba_gerador:
    st.subheader("🔮 Filtro Histórico (Rejeição Heurística)")
    
    # Campo para o usuário escolher o concurso alvo
    concurso_alvo = st.number_input("Estes palpites serão para qual concurso?", min_value=1, value=proximo_concurso_previsto, step=1)
    
    def get_quadrante(n):
        linha = (n - 1) // 10
        coluna = (n - 1) % 10
        if linha < 3: return 1 if coluna < 5 else 2
        else: return 3 if coluna < 5 else 4

    if st.button("🎲 Gerar 5 Palpites Inteligentes"):
        pesos = frequencias['Vezes Sorteado'].values + 1
        pesos_normalizados = pesos / pesos.sum()
        
        jogos_gerados = []
        with st.spinner("Filtrando combinações..."):
            while len(jogos_gerados) < 5:
                palpite_teste = np.random.choice(frequencias['Número'].values, size=6, replace=False, p=pesos_normalizados)
                pares = sum(1 for x in palpite_teste if x % 2 == 0)
                if pares not in [2, 3, 4]: continue
                
                colunas_usadas = set((x - 1) % 10 for x in palpite_teste)
                if len(colunas_usadas) < 4: continue
                
                quadrantes_usados = set(get_quadrante(x) for x in palpite_teste)
                if len(quadrantes_usados) < 3: continue
                
                palpite = list(palpite_teste)
                palpite.sort()
                
                if palpite not in jogos_gerados:
                    jogos_gerados.append(palpite)

        st.session_state['jogos_temp'] = jogos_gerados
        st.session_state['concurso_temp'] = concurso_alvo
        st.balloons()

    if 'jogos_temp' in st.session_state:
        st.success(f"🎯 Seus palpites para o concurso **{st.session_state['concurso_temp']}** estão prontos!")
        for i, jogo in enumerate(st.session_state['jogos_temp']):
            st.markdown(f"**Jogo {i+1}:** &nbsp; `{jogo[0]:02d}` - `{jogo[1]:02d}` - `{jogo[2]:02d}` - `{jogo[3]:02d}` - `{jogo[4]:02d}` - `{jogo[5]:02d}`")
            
        if st.button("💾 Salvar Palpites Oficiais no Supabase"):
            for jogo in st.session_state['jogos_temp']:
                registro = {
                    "concurso": st.session_state['concurso_temp'],
                    "bola_1": int(jogo[0]), "bola_2": int(jogo[1]), "bola_3": int(jogo[2]),
                    "bola_4": int(jogo[3]), "bola_5": int(jogo[4]), "bola_6": int(jogo[5])
                }
                supabase.table("meus_jogos").insert(registro).execute()
            
            del st.session_state['jogos_temp']
            st.success("✅ Jogos salvos com sucesso! Vá para a aba 'Conferidor de Jogos'.")
            st.rerun()

# ==========================================
# ABA 3: CONFERIDOR
# ==========================================
with aba_conferidor:
    st.subheader("✅ Conferidor Direcionado")
    
    meus_jogos_df = buscar_meus_jogos()
    
    if meus_jogos_df.empty or 'concurso' not in meus_jogos_df.columns:
        st.info("Você não tem jogos salvos com amarração de concurso. Gere e salve novos jogos na aba anterior!")
    else:
        # Descobre quais concursos o usuário apostou e ordena do maior para o menor
        concursos_apostados = sorted(meus_jogos_df['concurso'].dropna().unique().tolist(), reverse=True)
        
        # Cria um menu suspenso para o usuário escolher qual concurso quer conferir
        concurso_selecionado = st.selectbox("Selecione o concurso que deseja conferir:", concursos_apostados)
        
        # Filtra os jogos do usuário apenas para o concurso selecionado
        jogos_para_conferir = meus_jogos_df[meus_jogos_df['concurso'] == concurso_selecionado]
        
        st.write(f"Você tem **{len(jogos_para_conferir)}** jogo(s) registrado(s) para o concurso **{int(concurso_selecionado)}**.")
        st.divider()
        
        # Busca no DataFrame principal (df) se o resultado desse concurso já existe
        resultado_oficial = df[df['id'] == concurso_selecionado]
        
        if resultado_oficial.empty:
            st.warning(f"⏳ **Aguardando Sorteio!** O robô ainda não registrou o resultado oficial do concurso **{int(concurso_selecionado)}**. Verifique novamente após o sorteio da Caixa.")
            
            # Mostra apenas os bilhetes apostados sem conferir
            st.write("Sua Cartela de Apostas:")
            for index, row in jogos_para_conferir.iterrows():
                meu_jogo = [int(row['bola_1']), int(row['bola_2']), int(row['bola_3']), int(row['bola_4']), int(row['bola_5']), int(row['bola_6'])]
                jogo_str = " - ".join([f"{x:02d}" for x in sorted(meu_jogo)])
                st.markdown(f"- `{jogo_str}`")
                
        else:
            # O Sorteio já aconteceu! Vamos conferir!
            st.success("Sorteio realizado! Conferindo seus bilhetes...")
            
            # Pegando os números oficiais do banco da Caixa
            sorteio_oficial_set = set([
                int(resultado_oficial.iloc[0]['bola_1']), int(resultado_oficial.iloc[0]['bola_2']), int(resultado_oficial.iloc[0]['bola_3']),
                int(resultado_oficial.iloc[0]['bola_4']), int(resultado_oficial.iloc[0]['bola_5']), int(resultado_oficial.iloc[0]['bola_6'])
            ])
            
            for index, row in jogos_para_conferir.iterrows():
                meu_jogo_set = set([int(row['bola_1']), int(row['bola_2']), int(row['bola_3']), int(row['bola_4']), int(row['bola_5']), int(row['bola_6'])])
                
                acertos = sorteio_oficial_set.intersection(meu_jogo_set)
                qtd_acertos = len(acertos)
                
                jogo_str = " - ".join([f"{x:02d}" for x in sorted(list(meu_jogo_set))])
                acertos_str = " - ".join([f"{x:02d}" for x in sorted(list(acertos))]) if acertos else "Nenhum"
                
                col_jogo, col_resultado = st.columns([2, 1])
                with col_jogo:
                    st.markdown(f"**Bilhete:** `{jogo_str}`")
                    if qtd_acertos > 0:
                        st.caption(f"Acertou: **{acertos_str}**")
                
                with col_resultado:
                    if qtd_acertos == 6: st.success("🏆 SENA!")
                    elif qtd_acertos == 5: st.warning("🏅 QUINA!")
                    elif qtd_acertos == 4: st.info("🎖️ QUADRA!")
                    else: st.error(f"{qtd_acertos} acerto(s)")
                
                st.markdown("---")
