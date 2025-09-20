# 📈 Opções — Probabilidade de Exercício (Streamlit)

Aplicação para carregar um CSV de opções (B3) e gerar um **dashboard** com ranking de **probabilidade de exercício** (modelo **Black-Scholes**), separando **CALLs** e **PUTs**, com **gráficos** e **exportação para Excel**.

## Como rodar localmente
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Deploy no Streamlit Cloud (recomendado)
1. Suba estes arquivos para um repositório no GitHub (`app.py`, `requirements.txt`, `README.md`).
2. Acesse **https://share.streamlit.io** e conecte sua conta do GitHub.
3. Clique em **New app** → selecione o repositório, **branch** e **app file** = `app.py`.
4. Clique em **Deploy**.

> Dica: depois de publicado, você pode atualizar o app apenas dando *push* no GitHub.
