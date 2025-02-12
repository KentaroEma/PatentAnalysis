import streamlit as st
import os
import io  # ← `BytesIO` を使うために追加
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objs as go
from pdfminer.high_level import extract_text
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from datetime import datetime, timedelta
import time
import hashlib
from auth import check_password



# ページのレイアウト設定
st.set_page_config(
    page_title="Patent Analysis App.",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
    )

# PillowのDecompressionBombErrorのチェックを無効にする
Image.MAX_IMAGE_PIXELS = None


# ページ選択メニューをサイドバーに表示
st.sidebar.title("Navigation window")

pi = 3.14159265359
page_list = ["Home", "Patent", "Claim", "Others"]
analysis_list = ["Overview", "Applicant", "Others"]
margin = 1.1
OF = -0.93
cms = plt.cm.datad.keys()

page = st.sidebar.selectbox("Select measurements for analysis.", page_list)

# 📌 PDF のテキスト抽出をキャッシュする関数
@st.cache_data
def extract_text_from_pdf(file_bytes):
    """PDF のバイナリデータからテキストを抽出し、キャッシュする"""
    file_hash = hashlib.md5(file_bytes).hexdigest()  # ファイルのハッシュ値を取得
    with io.BytesIO(file_bytes) as pdf_file:  # `BytesIO` を使ってファイルオブジェクト化
        extracted_text = extract_text(pdf_file).replace(' ', '').replace('\n', '').replace('\u3000', '')
    return extracted_text, file_hash

# 📌 無限に色を生成する関数（HSLを使って自動生成）
def generate_color(index):
    hue = (index * 137.508) % 360  # 黄金比を使って色相を均等に分布
    return f"hsl({hue}, 75%, 75%)"

# 📌 テキストをHTML形式でハイライトする関数
def highlight_text(text, terms):
    for i, term in enumerate(terms):
        color = generate_color(i)  # 動的に色を決定
        text = re.sub(f"({re.escape(term)})", rf'<mark style="background-color: {color}">\1</mark>', text, flags=re.IGNORECASE)
    return text

# 各ページの内容
# Home
if page==page_list[0]:
    st.title(page_list[0])
    st.title("Patent Analysis App")
    st.write("Welcome to the Patent Analysis Application. Please select an analysis type from the sidebar.")

# Patent
elif page==page_list[1]:
    st.title(page_list[1])
    target_col = 'Patent'
    file_summaries = st.file_uploader("Upload CSV files", type='csv', accept_multiple_files=True)
    if len(file_summaries)>0:
        df_list = []
        for file_summary in file_summaries:
            df_summary = pd.read_csv(file_summary, encoding='utf-8', encoding_errors='ignore')
            df_list.append(df_summary)
        df = pd.concat(df_list).reset_index(drop=True)
        df = df.drop_duplicates(subset=['文献番号','出願日'], keep='first').reset_index(drop=True)
        target_date_col = st.sidebar.selectbox("Select date column", df.columns.to_list(), index=2)
        df[target_date_col] = pd.to_datetime(df[target_date_col])
        df['年'] = df[target_date_col].dt.year.astype('int')
        df['出願人/権利者'] = df['出願人/権利者'].astype('str')

        applicant_list =[]
        for applicants in df['出願人/権利者'].unique():
            applicants = applicants.replace('、',',')
            applicants = applicants.replace('，',',')
            applicants = applicants.replace(', ',',')
            applicants = applicants.replace(',　',',')
            applicants_split = str(applicants).split(',')
            for applicant in applicants_split:
                if applicant not in applicant_list:
                    if len(applicant)>1:
                        applicant_list.append(applicant)
        applicant_list.sort()
        
        # pandas.Timestamp → datetime.date に変換
        min_date = df[target_date_col].min().date()
        max_date = df[target_date_col].max().date()
        
        start_date = st.sidebar.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
        end_date = st.sidebar.date_input("End date", max_date, min_value=min_date, max_value=max_date)

        df_date = df[(df[target_date_col]>=str(start_date))&(df[target_date_col]<=str(end_date))]

        min_year = df_date['年'].min()
        max_year = df_date['年'].max()
        df_year = pd.DataFrame(range(min_year,max_year), columns=['年'])
        df_year['count'] = 0
        for year in range(min_year,max_year):
            df_year.loc[df_year['年']==year, 'count'] = df_date[df_date['年']==year]['文献番号'].count()

        stage_selector = st.sidebar.multiselect("Select stage type", df['ステージ'].unique(), default=df['ステージ'].unique(), key='stage_selector')
        for stage in stage_selector:
            for year in range(min_year,max_year):
                df_year.loc[df_year['年']==year, f'count_{stage}'] = df_date[(df_date['年']==year)&(df_date['ステージ']==stage)]['文献番号'].count()

        with st.spinner('Loading...'):
            # 出願人ごとの件数を計算
            df_applicant_initial = df_date.copy()
            df_applicant_initial['出願人/権利者'] = df_applicant_initial['出願人/権利者'].str.split('[、，,]')  # 出願人名を分割
            df_applicant_initial = df_applicant_initial.explode('出願人/権利者')  # 出願人名ごとにデータを展開
            # 総件数を集計
            df_applicant_grouped = df_applicant_initial.groupby('出願人/権利者')['文献番号'].count().reset_index(drop=False)
            df_applicant_grouped.rename(columns={'文献番号': '件数'}, inplace=True)
            # ステージごとの件数を集計
            df_stage_grouped = df_applicant_initial.groupby(['出願人/権利者', 'ステージ'])['文献番号'].count().unstack(fill_value=0)
            df_stage_grouped.columns = [f'ステージ_{stage}' for stage in df_stage_grouped.columns]  # 列名を変更
            df_stage_grouped.reset_index(drop=False, inplace=True)
            # 年ごとの件数を集計
            df_year_grouped = df_applicant_initial.groupby(['出願人/権利者', '年'])['文献番号'].count().unstack(fill_value=0)
            df_year_grouped.columns = [f"{year}年" for year in df_year_grouped.columns]  # 列名を変更
            df_year_grouped.reset_index(drop=False, inplace=True)
            # すべてのデータを統合
            df_applicant = df_applicant_grouped.merge(df_stage_grouped, on='出願人/権利者', how='left')
            df_applicant = df_applicant.merge(df_year_grouped, on='出願人/権利者', how='left')
            # 出願人の件数順にソート
            df_applicant.sort_values('件数', ascending=False, inplace=True)

        applicant = st.sidebar.selectbox("Select applicant", df_applicant['出願人/権利者'].unique(), index=0)

        tab_overview, tab_applicant, tab_others = st.tabs(analysis_list)

        with tab_overview:
            st.header(analysis_list[0])
            st.write("This is an overview analysis page.")
            st.write("Please select the date range you want to analyze.")
            st.write("The selected date range is from {} to {}.".format(start_date, end_date))
            st.write("The data is as follows.")

            # データの表示
            st.write(df_date)

            # データの可視化
            st.header("Visualization")
            with st.spinner('Visualizing...'):
                fig1 = go.Figure()
                fig1.update_layout(title='Patents every year', xaxis_title='Year', yaxis_title='Counts')
                fig1.add_trace(go.Scatter(x=df_year['年'].values, y=df_year['count'].values, mode='lines+markers', name='Counts every year (All)'))
                for stage in stage_selector:
                    fig1.add_trace(go.Scatter(x=df_year['年'].values, y=df_year[f'count_{stage}'].values, mode='lines+markers', name=f'Counts every year ({stage})'))
                st.plotly_chart(fig1)

        with tab_applicant:
            st.header(analysis_list[1])
            st.write("This is an applicant analysis page.")

            df_applicant.sort_values('件数', ascending=False, inplace=True)

            # データの表示
            st.write(df_applicant)

            num_applicant = st.slider("Number of applicants", 1, len(df_applicant), 50)

            # データの可視化
            st.header("Visualization")
            with st.spinner('Visualizing...'):
                fig2 = go.Figure()
                # ステージごとのデータがある場合、各ステージを積み上げ棒グラフにする
                for stage in df_applicant.columns:
                    if stage.startswith("ステージ_"):  # ステージ関連のカラムのみを対象
                        fig2.add_trace(go.Bar(
                            x=df_applicant[stage].values[:num_applicant],
                            y=df_applicant['出願人/権利者'].values[:num_applicant],
                            name=stage.replace("ステージ_", ""),  # ラベルをシンプルに
                            orientation='h'
                            ))
                fig2.update_layout(
                    title='Patents per Applicant',
                    height=1200,
                    width=900,
                    xaxis_title='Counts',
                    yaxis_title='Applicants',
                    yaxis=dict(autorange="reversed"),  # 件数が多い順に上から表示
                    barmode='stack'  # 積み上げ棒グラフ
                    )
                st.plotly_chart(fig2)

            with st.spinner("Visualizing..."):
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(
                    x=df_year_grouped.columns.to_list()[1:], 
                    y=df_year_grouped[df_year_grouped['出願人/権利者'].str.contains(applicant)].T.iloc[:,0].to_list()[1:],
                    mode='lines+markers',
                    name='Patents per Stage'
                    ))
                fig3.update_layout(
                    title=f'Patents per Applicant ({applicant})',
                    xaxis_title='Year',
                    yaxis_title='Counts'
                    )
                st.plotly_chart(fig3)

        with tab_others:
            st.header(analysis_list[2])
            st.write("Coming soon...")



# Claim
elif page==page_list[2]:
    st.title(page_list[2])
    target_col = 'Claim'
    file_pdfs = st.file_uploader("Upload PDF files", type='pdf', accept_multiple_files=True)

    total_files = len(file_pdfs)  # 全ファイル数

    pdf_name_list = []
    pdf_text_dict = {}  # ハッシュキーでキャッシュ管理する辞書

    if len(file_pdfs)>0:
        extract_bar = st.progress(0)  # プログレスバーの追加
        with st.spinner('Loading...'):
            for i, file_pdf in enumerate(file_pdfs):
                # 📌 ファイルのバイナリデータを取得し、キャッシュをチェック
                file_bytes = file_pdf.read()
                extracted_text, file_hash = extract_text_from_pdf(file_bytes)
                pdf_name_list.append(file_pdf.name)
                pdf_text_dict[file_hash] = extracted_text  # ハッシュキーで保存

                extract_bar.progress((i+1)/total_files, f"Extracting {i+1}/{total_files}")
                time.sleep(0.2)

        extract_bar.empty()  # すべての処理が完了したらプログレスバーを消す

    # サイドバーに検索ボックスを追加（カンマ区切りで複数入力）
    search_query = st.sidebar.text_input("Enter keywords (comma separated)", "")
    # 検索ワードをリストに変換（カンマで分割して前後の空白を削除）
    search_terms = [term.strip() for term in search_query.split(',') if term.strip()]

    if len(file_pdfs)>0:
        display_bar = st.progress(0)  # プログレスバーの追加
        st.write("Search terms: ", search_terms)
        with st.spinner('Loading...'):
            for i, (name, text) in enumerate(zip(pdf_name_list, pdf_text_dict.values())):
                text = text.replace(' ','')
                st.header(f"{i+1}/{total_files}: {name}")  # ファイル名の表示
                try:
                    subject = text.split('【課題】')[1].split('【解決手段】')[0]
                    subject = subject.replace('\n','')
                    subject = subject.replace('\u3000','')
                    subject = highlight_text(subject, search_terms)  # 🔍 ハイライト処理
                    st.markdown(f'**【課題】**<br>{subject}', unsafe_allow_html=True)
                    # st.write('【課題】'+subject)
                except:
                    pass
                try:
                    solution = text.split('【解決手段】')[1].split('【選択図】')[0]
                    solution = solution.replace('\n','')
                    solution = solution.replace('\u3000','')
                    solution = highlight_text(solution, search_terms)  # 🔍 ハイライト処理
                    st.markdown(f'**【解決手段】**<br>{solution}', unsafe_allow_html=True)
                    # st.write('【解決手段】'+solution)
                except:
                    pass
                try:
                    figure = text.split('【選択図】')[1].split('【特許請求の範囲】')[0]
                    figure = figure.replace('\n','')
                    figure = figure.replace('\u3000','')
                    st.write('【選択図】'+figure)
                except:
                    pass
                try:
                    claims = text.split('【特許請求の範囲】')[1].split('【発明の詳細な説明】')[0]
                    claims = claims.replace('\n','')
                    claims = claims.replace('\u3000','')
                    claims_list = claims.split('【請求項')
                    for claim in claims_list:
                        if claim != '': 
                            claim_text = highlight_text('【請求項' + claim, search_terms)  # 🔍 ハイライト処理
                            st.markdown(claim_text, unsafe_allow_html=True)
                            # st.write('【請求項'+claim)
                except:
                    pass

                # 📌 プログレスバーを更新
                display_bar.progress((i+1)/total_files, f"Processing {i+1}/{total_files}")
                # 📌 少し待機（見やすくするため）
                time.sleep(0.2)

        display_bar.empty()  # すべての処理が完了したらプログレスバーを消す

        st.header("EOF")


# Others
elif page==page_list[3]:
    st.title(page_list[3])
    st.write("This is a page for other analysis.")