
import io
import math
from datetime import datetime, date
import numpy as np
import pandas as pd
import streamlit as st
from math import log, sqrt
from scipy.stats import norm
import matplotlib.pyplot as plt

st.set_page_config(page_title="Opções - Probabilidade de Exercício", layout="wide")

st.title("📈 Dashboard de Probabilidade de Exercício de Opções")
st.caption("Envie seu arquivo CSV e veja o ranking por probabilidade de exercício (Black‑Scholes).")

# Sidebar inputs
st.sidebar.header("⚙️ Parâmetros")
expiry = st.sidebar.date_input("Data de vencimento", value=date(2025, 9, 26))
r = st.sidebar.number_input("Taxa livre de risco (a.a.)", min_value=0.0, max_value=1.0, value=0.0, step=0.01, format="%.4f")
vol_list_default = "0.25,0.35,0.45"
vol_str = st.sidebar.text_input("Volatilidades anualizadas (separadas por vírgula)", value=vol_list_default)
vols = []
for token in vol_str.split(","):
    try:
        v = float(token.strip())
        if v > 0:
            vols.append(v)
    except:
        pass
if not vols:
    vols = [0.25, 0.35, 0.45]

uploaded = st.file_uploader("Carregue seu arquivo CSV", type=["csv"])

def limpar_valor(x):
    x = str(x)
    x = x.replace("R$", "").replace("\u00a0", " ").strip()
    # remove separador de milhar '.' e troca ',' por '.'
    x = x.replace(".", "").replace(",", ".")
    return x

def parse_csv(file_buf):
    # Tentar primeiro separador vírgula
    file_buf.seek(0)
    df = pd.read_csv(file_buf, sep=",", engine="python")
    if df.shape[1] == 1:
        # Tentar ponto e vírgula
        file_buf.seek(0)
        df = pd.read_csv(file_buf, sep=";", engine="python")
    return df

def ensure_columns(df):
    required = ["ACAO CODIGO", "OPCAO", "VALOR AÇÃO", "STRIKE R$", "DISTANCIA  % STRIKE", "VECTO", "TIPO"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas faltando no CSV: {missing}. Esperado: {required}")
    return df

def to_float_series(s, is_percent=False):
    if is_percent:
        s = s.astype(str).str.replace("%", "", regex=False)
    s = s.apply(limpar_valor)
    return pd.to_numeric(s, errors="coerce")

def prob_exercicio(S, K, sigma, r, T, tipo):
    if S <= 0 or K <= 0 or sigma <= 0 or T <= 0:
        return np.nan
    d2 = (log(S / K) + (r - 0.5 * sigma**2) * T) / (sigma * sqrt(T))
    if str(tipo).upper().strip() == "CV":   # CALL
        return norm.cdf(d2)
    else:  # PUT
        return norm.cdf(-d2)

def build_excel(calls, puts, params, top_calls_img=None, top_puts_img=None):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        calls.to_excel(writer, sheet_name="CALLs", index=False)
        puts.to_excel(writer, sheet_name="PUTs", index=False)
        params.to_excel(writer, sheet_name="Parâmetros", index=False)
        workbook = writer.book
        if top_calls_img is not None:
            ws = writer.sheets["CALLs"]
            ws.insert_image("M2", "top_calls.png", {"image_data": top_calls_img})
        if top_puts_img is not None:
            ws = writer.sheets["PUTs"]
            ws.insert_image("M2", "top_puts.png", {"image_data": top_puts_img})
    output.seek(0)
    return output

if uploaded is None:
    st.info("👆 Envie o CSV para começar. Exemplo de colunas esperadas: 'ACAO CODIGO', 'OPCAO', 'VALOR AÇÃO', 'STRIKE R$', 'DISTANCIA  % STRIKE', 'VECTO', 'TIPO'.")
else:
    try:
        df_raw = parse_csv(uploaded)
        df = ensure_columns(df_raw.copy())

        # Conversões
        df["VALOR AÇÃO"] = to_float_series(df["VALOR AÇÃO"])
        df["STRIKE R$"] = to_float_series(df["STRIKE R$"])
        if "DISTANCIA  % STRIKE" in df.columns:
            df["DISTANCIA  % STRIKE"] = to_float_series(df["DISTANCIA  % STRIKE"], is_percent=True)
        else:
            df["DISTANCIA  % STRIKE"] = (df["VALOR AÇÃO"] / df["STRIKE R$"] - 1) * 100

        # Prazo T
        today = datetime.now().date()
        T = max((expiry - today).days, 0) / 365.0

        # Probabilidades por cenário + média
        for v in vols:
            df[f"Prob ITM @ {int(v*100)}%"] = df.apply(
                lambda row: prob_exercicio(
                    row["VALOR AÇÃO"], row["STRIKE R$"], v, r, max(T, 1e-8), row["TIPO"]
                ), axis=1
            )
        prob_cols = [c for c in df.columns if c.startswith("Prob ITM @")]
        df["Prob ITM (médio)"] = df[prob_cols].mean(axis=1)

        # Separar CALLs / PUTs e ordenar
        calls = df[df["TIPO"].astype(str).str.upper().str.strip() == "CV"].copy()
        puts = df[df["TIPO"].astype(str).str.upper().str.strip() == "PV"].copy()
        calls.sort_values("Prob ITM (médio)", ascending=False, inplace=True)
        puts.sort_values("Prob ITM (médio)", ascending=False, inplace=True)

        # Classificação textual
        def label(p):
            if pd.isna(p):
                return "Sem cálculo"
            if p >= 0.70:
                return "Alta chance de exercício"
            elif p >= 0.40:
                return "Média chance de exercício"
            else:
                return "Baixa chance de exercício"
        calls["Interpretação"] = calls["Prob ITM (médio)"].apply(label)
        puts["Interpretação"] = puts["Prob ITM (médio)"].apply(label)

        # Formatação para exibição
        fmt_cols = prob_cols + ["Prob ITM (médio)"]
        calls_show = calls.copy()
        puts_show = puts.copy()
        for c in fmt_cols:
            calls_show[c] = (calls_show[c] * 100).map(lambda x: f"{x:.1f}%")
            puts_show[c] = (puts_show[c] * 100).map(lambda x: f"{x:.1f}%")

        calls_show["VALOR AÇÃO"] = calls_show["VALOR AÇÃO"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        calls_show["STRIKE R$"] = calls_show["STRIKE R$"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        puts_show["VALOR AÇÃO"] = puts_show["VALOR AÇÃO"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        puts_show["STRIKE R$"] = puts_show["STRIKE R$"].map(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Layout
        st.subheader("Ranking por Probabilidade (CALLs)")
        st.dataframe(calls_show.reset_index(drop=True), use_container_width=True)
        st.subheader("Ranking por Probabilidade (PUTs)")
        st.dataframe(puts_show.reset_index(drop=True), use_container_width=True)

        # Gráficos Top 10
        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Top 10 CALLs — Prob. média**")
            fig = plt.figure(figsize=(8,4.5))
            top_calls = calls.head(10)
            plt.bar(top_calls["OPCAO"], top_calls["Prob ITM (médio)"])
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Probabilidade")
            st.pyplot(fig)

        with col2:
            st.markdown("**Top 10 PUTs — Prob. média**")
            fig2 = plt.figure(figsize=(8,4.5))
            top_puts = puts.head(10)
            plt.bar(top_puts["OPCAO"], top_puts["Prob ITM (médio)"])
            plt.xticks(rotation=45, ha="right")
            plt.ylabel("Probabilidade")
            st.pyplot(fig2)

        # Exportar Excel
        st.markdown("---")
        st.subheader("⬇️ Exportar Excel")
        params_df = pd.DataFrame({
            "Parâmetro": ["Data de referência (local)", "Vencimento", "Dias até o vencimento", "T (anos)",
                          "r (a.a.)", "Volatilidades (cenários)"],
            "Valor": [today.strftime("%d/%m/%Y"), expiry.strftime("%d/%m/%Y"), max((expiry - today).days, 0), round(T, 6),
                      f"{r:.2%}".replace(".", ","), ", ".join([f"{v:.0%}".replace(".", ",") for v in vols])]
        })

        # Render imagens em memória para inserir no Excel
        buf_calls = io.BytesIO()
        fig = plt.figure(figsize=(8,4.5))
        top_calls = calls.head(10)
        plt.bar(top_calls["OPCAO"], top_calls["Prob ITM (médio)"])
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Probabilidade")
        plt.tight_layout()
        fig.savefig(buf_calls, format="png")
        plt.close(fig)
        buf_calls.seek(0)

        buf_puts = io.BytesIO()
        fig2 = plt.figure(figsize=(8,4.5))
        top_puts = puts.head(10)
        plt.bar(top_puts["OPCAO"], top_puts["Prob ITM (médio)"])
        plt.xticks(rotation=45, ha="right")
        plt.ylabel("Probabilidade")
        plt.tight_layout()
        fig2.savefig(buf_puts, format="png")
        plt.close(fig2)
        buf_puts.seek(0)

        excel_bytes = build_excel(
            calls_show, puts_show, params_df, top_calls_img=buf_calls, top_puts_img=buf_puts
        )

        st.download_button(
            label="Baixar Excel (CALLs, PUTs, gráficos, parâmetros)",
            data=excel_bytes,
            file_name="probabilidade_exercicio_dashboard.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

        st.success("Pronto! Ajuste os parâmetros na barra lateral para refinar o cálculo.")
    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o arquivo: {e}")
        st.stop()
