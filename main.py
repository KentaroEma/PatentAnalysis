import streamlit as st
import os
import io
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objs as go
from sklearn.cluster import KMeans
from pdfminer.high_level import extract_text
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from datetime import datetime, timedelta
import time
import hashlib

# --- 認証機能 ---
# auth.py が存在する場合は認証を実施（存在しない場合は警告表示）
# try:
#     from auth import check_password
#     if not check_password():
#          st.error("認証に失敗しました。")
#          st.stop()
# except ImportError:
#     st.warning("認証機能が利用できません。")

# --- ページのレイアウト設定 ---
st.set_page_config(
    page_title="Patent Analysis App.",
    page_icon="🧊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# PillowのDecompressionBombErrorのチェックを無効化（大きな画像には注意）
Image.MAX_IMAGE_PIXELS = None

# --- サイドバー：ページ選択 ---
st.sidebar.title("Navigation window")
page_list = ["Home", "Patent", "Claim", "Others"]
analysis_list = ["Overview", "Applicant", "FI", "Summary"]
page = st.sidebar.selectbox("Select measurements for analysis.", page_list)

# --- FIコード処理関連 ---
def merge_fi_codes(fi_list):
    """FIコードのリスト中、数字のみのエントリは直前のコードと結合する"""
    merged_list = []
    prev_fi = None
    for fi in fi_list:
        if fi.split('@')[0].isdigit() and prev_fi:
            merged_list[-1] = f"{prev_fi}-{fi}"
        else:
            merged_list.append(fi)
            prev_fi = fi
    return merged_list

def parse_fi_codes(fi_list):
    """FIコードをセクション、クラス、サブクラス、グループに分解する"""
    sections, classes, subclasses, groups = set(), set(), set(), set()
    for fi in fi_list:
        parts = fi.split("/")
        if len(parts) >= 2:
            main_part = parts[0]
            if len(main_part) >= 1:
                sections.add(main_part[0])
            if len(main_part) >= 4:
                subclasses.add(main_part[:4])
            if len(main_part) >= 3:
                classes.add(main_part[:3])
            groups.add(fi.split('-')[0].split('@')[0])
    return list(sections), list(classes), list(subclasses), list(groups)

# --- PDFテキスト抽出（キャッシュ付き） ---
@st.cache_data
def extract_text_from_pdf(file_bytes):
    """
    PDF のバイナリデータからテキストを抽出し、
    改行や余分な空白を正規化する
    """
    file_hash = hashlib.md5(file_bytes).hexdigest()
    try:
        with io.BytesIO(file_bytes) as pdf_file:
            extracted_text = extract_text(pdf_file)
            # 連続する空白や改行を1つのスペースに置換
            extracted_text = re.sub(r'\s+', ' ', extracted_text).strip()
    except Exception as e:
        st.error(f"PDFテキスト抽出エラー: {e}")
        extracted_text = ""
    return extracted_text, file_hash

# --- 色自動生成・テキストハイライト ---
def generate_color(index):
    hue = (index * 137.508) % 360  # 黄金比に基づく均等な色分布
    return f"hsl({hue}, 75%, 75%)"

def highlight_text(text, terms):
    for i, term in enumerate(terms):
        color = generate_color(i)
        text = re.sub(f"({re.escape(term)})", rf'<mark style="background-color: {color}">\1</mark>', text, flags=re.IGNORECASE)
    return text

# --- 各ページの内容 ---

# Home ページ
if page == page_list[0]:
    st.title("Home")
    st.title("Patent Analysis App")
    st.write("Welcome to the Patent Analysis Application")
    st.write("This application is for analyzing patent data.")
    st.write("1. Find some patents from [J-PlatPat](https://www.j-platpat.inpit.go.jp/).")
    st.write("2. Download the patent data as CSV files or PDF files.")
    st.write("3. Select the analysis type from the sidebar.")
    st.write("4. Upload the CSV files or PDF files.")

# Patent ページ
elif page == page_list[1]:
    st.title("Patent")
    target_col = 'Patent'
    file_summaries = st.file_uploader("Upload CSV files", type='csv', accept_multiple_files=True)
    if file_summaries:
        df_list = []
        for file_summary in file_summaries:
            try:
                df_summary = pd.read_csv(file_summary, encoding='utf-8', encoding_errors='ignore')
                df_list.append(df_summary)
            except Exception as e:
                st.error(f"CSV読み込みエラー: {file_summary.name} - {e}")
        if df_list:
            df = pd.concat(df_list).reset_index(drop=True)
            df = df.drop_duplicates(subset=['文献番号','出願日'], keep='first').reset_index(drop=True)
            date_cols = [col for col in df.columns if col.endswith('日')]
            if not date_cols:
                st.error("日付カラムが見つかりません。")
            else:
                target_date_col = st.sidebar.selectbox("Select date column", date_cols)
                try:
                    df[target_date_col] = pd.to_datetime(df[target_date_col])
                except Exception as e:
                    st.error(f"日付変換エラー: {e}")
                df['年'] = df[target_date_col].dt.year.astype('int')
                df['出願人/権利者'] = df['出願人/権利者'].astype('str')
                df['FI'] = df['FI'].astype('str').apply(lambda x: [fi.strip() for fi in x.split(',') if fi.strip()])
                df['FI'] = df['FI'].apply(merge_fi_codes)
                df[['セクション', 'クラス', 'サブクラス', 'グループ']] = df['FI'].apply(lambda x: pd.Series(parse_fi_codes(x)))

                # --- 出願人リストの正規化 ---
                applicant_list = []
                for applicants in df['出願人/権利者'].unique():
                    applicants = applicants.replace('、',',').replace('，',',').replace(', ',',').replace(',　',',')
                    for applicant in applicants.split(','):
                        if applicant not in applicant_list and len(applicant) > 1:
                            applicant_list.append(applicant)
                applicant_list.sort()
                
                # --- 日付フィルタ ---
                min_date = df[target_date_col].min().date()
                max_date = df[target_date_col].max().date()
                start_date = st.sidebar.date_input("Start date", min_date, min_value=min_date, max_value=max_date)
                end_date = st.sidebar.date_input("End date", max_date, min_value=min_date, max_value=max_date)
                df_date = df[(df[target_date_col] >= pd.to_datetime(start_date)) & (df[target_date_col] <= pd.to_datetime(end_date))]

                # --- 年別・ステージ別件数の集計 ---
                min_year = df_date['年'].min()
                max_year = df_date['年'].max() + 1
                df_year = pd.DataFrame(range(min_year, max_year), columns=['年'])
                df_year['count'] = 0
                for year in range(min_year, max_year):
                    df_year.loc[df_year['年'] == year, 'count'] = df_date[df_date['年'] == year]['文献番号'].count()
                stage_selector = st.sidebar.multiselect("Select stage type", df['ステージ'].unique(), default=df['ステージ'].unique(), key='stage_selector')
                for stage in stage_selector:
                    for year in range(min_year, max_year):
                        df_year.loc[df_year['年'] == year, f'count_{stage}'] = df_date[(df_date['年'] == year) & (df_date['ステージ'] == stage)]['文献番号'].count()
                fi_selector = st.sidebar.multiselect("Select FI Section code", df['セクション'].explode().unique(), default=df['セクション'].explode().unique(), key='fi_section_selector')
                df_fi = df_date[df_date['セクション'].apply(lambda x: any(fi in x for fi in fi_selector))]

                # --- 出願人別集計 ---
                with st.spinner('Loading data and computing statistics...'):
                    df_applicant_initial = df_date.copy()
                    df_applicant_initial['出願人/権利者'] = df_applicant_initial['出願人/権利者'].str.split('[、，,]')
                    df_applicant_initial = df_applicant_initial.explode('出願人/権利者')
                    df_applicant_grouped = df_applicant_initial.groupby('出願人/権利者')['文献番号'].count().reset_index()
                    df_applicant_grouped.rename(columns={'文献番号': '件数'}, inplace=True)
                    df_stage_grouped = df_applicant_initial.groupby(['出願人/権利者', 'ステージ'])['文献番号'].count().unstack(fill_value=0)
                    df_stage_grouped.columns = [f'ステージ_{stage}' for stage in df_stage_grouped.columns]
                    df_stage_grouped.reset_index(inplace=True)
                    df_year_grouped = df_applicant_initial.groupby(['出願人/権利者', '年'])['文献番号'].count().unstack(fill_value=0)
                    df_year_grouped.columns = [f"{year}年" for year in df_year_grouped.columns]
                    df_year_grouped.reset_index(inplace=True)
                    df_applicant = df_applicant_grouped.merge(df_stage_grouped, on='出願人/権利者', how='left')
                    df_applicant = df_applicant.merge(df_year_grouped, on='出願人/権利者', how='left')
                    df_applicant.sort_values('件数', ascending=False, inplace=True)
                
                # --- ダウンロード機能（フィルタ済データCSV） ---
                csv_data = df_date.to_csv(index=False).encode('utf-8')
                st.download_button("Download Filtered Data as CSV", csv_data, "filtered_patents.csv", "text/csv")
                
                applicant = st.sidebar.selectbox("Select applicant", df_applicant['出願人/権利者'].unique(), index=0)

                # --- タブ表示 ---
                tab_overview, tab_applicant, tab_fi, tab_summary = st.tabs(analysis_list)

                # Overview タブ
                with tab_overview:
                    st.header("Overview")
                    st.write("This is an overview analysis page.")
                    st.write(f"The selected date range is from {start_date} to {end_date}.")
                    st.dataframe(df_date)
                    st.header("Visualization")
                    with st.spinner('Visualizing...'):
                        fig1 = go.Figure()
                        fig1.update_layout(title='Patents every year', xaxis_title='Year', yaxis_title='Counts')
                        fig1.add_trace(go.Scatter(
                            x=df_year['年'].values, 
                            y=df_year['count'].values, 
                            mode='lines+markers', 
                            name='Counts every year (All)'
                        ))
                        for stage in stage_selector:
                            fig1.add_trace(go.Scatter(
                                x=df_year['年'].values, 
                                y=df_year[f'count_{stage}'].values, 
                                mode='lines+markers', 
                                name=f'Counts every year ({stage})'
                            ))
                        st.plotly_chart(fig1)

                # Applicant タブ
                with tab_applicant:
                    st.header("Applicant")
                    st.write("This is an applicant analysis page.")
                    st.write(df_applicant)
                    num_applicant = st.slider("Number of applicants", 1, len(df_applicant), 50)
                    st.header("Visualization")
                    with st.spinner('Visualizing...'):
                        fig2 = go.Figure()
                        for col in df_applicant.columns:
                            if col.startswith("ステージ_"):
                                fig2.add_trace(go.Bar(
                                    x=df_applicant[col].values[:num_applicant],
                                    y=df_applicant['出願人/権利者'].values[:num_applicant],
                                    name=col.replace("ステージ_", ""),
                                    orientation='h'
                                ))
                        fig2.update_layout(
                            title='Patents per Applicant',
                            height=1200,
                            width=900,
                            xaxis_title='Counts',
                            yaxis_title='Applicants',
                            yaxis=dict(autorange="reversed"),
                            barmode='stack'
                        )
                        st.plotly_chart(fig2)
                    
                    with st.spinner("Visualizing applicant trends..."):
                        fig3 = go.Figure()
                        try:
                            applicant_year_data = df_year_grouped[df_year_grouped['出願人/権利者'] == applicant]
                            if not applicant_year_data.empty:
                                years = [int(col.replace('年', '')) for col in applicant_year_data.columns if col.endswith('年')]
                                counts = [applicant_year_data[col].values[0] for col in applicant_year_data.columns if col.endswith('年')]
                                fig3.add_trace(go.Scatter(
                                    x=years,
                                    y=counts,
                                    mode='lines+markers',
                                    name='Patents per Year'
                                ))
                                fig3.update_layout(
                                    title=f'Patents per Applicant ({applicant})',
                                    xaxis_title='Year',
                                    yaxis_title='Counts'
                                )
                                st.plotly_chart(fig3)
                        except Exception as e:
                            st.error(f"年次データの可視化エラー: {e}")
                    
                    # バブルチャートによる年次データの可視化
                    df_applicant_melted = df_applicant[:num_applicant].melt(
                        id_vars=['出願人/権利者'],
                        value_vars=[col for col in df_applicant.columns if col.endswith('年')],
                        var_name='年',
                        value_name='出願件数'
                    )
                    df_applicant_melted['年'] = df_applicant_melted['年'].str.replace('年', '').astype(int)
                    with st.spinner('Visualizing bubble chart...'):
                        fig_bubble = go.Figure()
                        for app in df_applicant_melted['出願人/権利者'].unique():
                            df_subset = df_applicant_melted[df_applicant_melted['出願人/権利者'] == app]
                            fig_bubble.add_trace(go.Scatter(
                                x=df_subset['年'],
                                y=[app] * len(df_subset),
                                mode='markers',
                                marker=dict(
                                    size=df_subset['出願件数'] * 2,
                                    opacity=0.6,
                                    line=dict(width=1, color='black')
                                ),
                                name=app
                            ))
                        fig_bubble.update_layout(
                            title="Applicant-wise Annual Patent Applications (Bubble Chart)",
                            xaxis_title="Year",
                            yaxis_title="Applicants",
                            yaxis=dict(autorange="reversed"),
                            showlegend=True,
                            height=1600,
                            width=1200
                        )
                        st.plotly_chart(fig_bubble)
                    
                    # --- クラスタリング分析の追加機能 ---
                    st.subheader("Clustering Analysis on Applicants")
                    num_clusters = st.slider("Select number of clusters", 2, 10, 3, key="clusters_slider")
                    clustering_features = df_applicant.filter(regex='^(件数|ステージ_)').fillna(0)
                    if not clustering_features.empty:
                        kmeans = KMeans(n_clusters=num_clusters, random_state=42)
                        df_applicant['cluster'] = kmeans.fit_predict(clustering_features)
                        st.write("Clustering results:")
                        st.dataframe(df_applicant[['出願人/権利者', '件数', 'cluster']])
                        cluster_counts = df_applicant['cluster'].value_counts().sort_index()
                        fig_cluster = go.Figure(go.Bar(
                            x=cluster_counts.index.astype(str),
                            y=cluster_counts.values
                        ))
                        fig_cluster.update_layout(title="Number of Applicants in each Cluster", xaxis_title="Cluster", yaxis_title="Count")
                        st.plotly_chart(fig_cluster)

                # FI タブ
                with tab_fi:
                    st.header("FI")
                    fi_reference_url = 'https://www.j-platpat.inpit.go.jp/cache/classify/patent/PMGS_HTML/jpp/FI/ja/fiSection/fiSection.html'
                    st.write(f"Please refer to the following URL for the FI classification: [J-PlatPat:FIセクション/広域ファセット選択📌]({fi_reference_url})")
                    fig4 = go.Figure()
                    fig4.add_trace(go.Pie(
                        labels=df_fi['セクション'].explode().value_counts().index,
                        values=df_fi['セクション'].explode().value_counts().values,
                        rotation=0,
                        hole=0.3,
                        title='FI Section',
                        textinfo='label+percent',
                    ))
                    fig4.update_layout(title='FI Section', height=800, width=800)
                    st.plotly_chart(fig4)
                    fig5 = go.Figure()
                    fig5.add_trace(go.Bar(
                        x=df_fi['クラス'].explode().value_counts().index,
                        y=df_fi['クラス'].explode().value_counts().values,
                        name='FI Class',
                    ))
                    fig5.update_layout(title='FI Class', height=600, width=1200, xaxis_title='FI Class', yaxis_title='Counts')
                    st.plotly_chart(fig5)

                # Summary タブ
                with tab_summary:
                    st.header("Summary")
                    if '要約' not in df.columns.to_list():
                        st.write("There is no summary data in the uploaded file.")
                    else:
                        st.write(df_date[['文献番号','出願人/権利者','要約']])
    else:
        st.info("CSVファイルをアップロードしてください。")

# Claim ページ
elif page == page_list[2]:
    st.title("Claim")
    target_col = 'Claim'
    file_pdfs = st.file_uploader("Upload PDF files", type='pdf', accept_multiple_files=True)
    total_files = len(file_pdfs)
    pdf_name_list = []
    pdf_text_dict = {}
    if file_pdfs:
        extract_bar = st.progress(0)
        with st.spinner('Extracting PDF texts...'):
            for i, file_pdf in enumerate(file_pdfs):
                try:
                    file_bytes = file_pdf.read()
                    extracted_text, file_hash = extract_text_from_pdf(file_bytes)
                    pdf_name_list.append(file_pdf.name)
                    pdf_text_dict[file_hash] = extracted_text
                except Exception as e:
                    st.error(f"{file_pdf.name} のテキスト抽出エラー: {e}")
                extract_bar.progress((i+1)/total_files)
                time.sleep(0.1)
            extract_bar.empty()
    # --- 抽出結果のダウンロード ---
    if pdf_text_dict:
        pdf_df = pd.DataFrame({
            "file_name": pdf_name_list,
            "extracted_text": list(pdf_text_dict.values())
        })
        csv_pdf = pdf_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Extracted PDF Texts as CSV", csv_pdf, "extracted_pdf_texts.csv", "text/csv")
        
    search_query = st.sidebar.text_input("Enter keywords (comma separated)", "")
    search_terms = [term.strip() for term in search_query.split(',') if term.strip()]
    if pdf_text_dict:
        display_bar = st.progress(0)
        st.write("Search terms: ", search_terms)
        with st.spinner('Processing PDFs...'):
            for i, (name, text) in enumerate(zip(pdf_name_list, pdf_text_dict.values())):
                with st.expander(f"{i+1}/{total_files}: {name}", expanded=True):
                    st.header(f"{i+1}/{total_files}: {name}")
                    text = re.sub(r'\s+', ' ', text)
                    try:
                        subject = text.split('【課題】')[1].split('【解決手段】')[0].strip()
                        subject = highlight_text(subject, search_terms)
                        st.markdown(f'**【課題】**<br>{subject}', unsafe_allow_html=True)
                    except IndexError:
                        st.warning("【課題】セクションの抽出に失敗しました。")
                    try:
                        solution = text.split('【解決手段】')[1].split('【選択図】')[0].strip()
                        solution = highlight_text(solution, search_terms)
                        st.markdown(f'**【解決手段】**<br>{solution}', unsafe_allow_html=True)
                    except IndexError:
                        st.warning("【解決手段】セクションの抽出に失敗しました。")
                    try:
                        figure = text.split('【選択図】')[1].split('【特許請求の範囲】')[0].strip()
                        st.markdown(f'**【選択図】**<br>{figure}', unsafe_allow_html=True)
                    except IndexError:
                        st.warning("【選択図】セクションの抽出に失敗しました。")
                    try:
                        claims = text.split('【特許請求の範囲】')[1].split('【発明の詳細な説明】')[0].strip()
                        claims_list = claims.split('【請求項')
                        st.markdown(f'**【特許請求の範囲】**<br>', unsafe_allow_html=True)
                        for claim in claims_list:
                            if claim:
                                claim_text = highlight_text('【請求項' + claim, search_terms)
                                st.markdown(claim_text, unsafe_allow_html=True)
                    except IndexError:
                        st.warning("【特許請求の範囲】セクションの抽出に失敗しました。")
                    display_bar.progress((i+1)/total_files)
                    time.sleep(0.1)
            display_bar.empty()
        st.header("EOF")
    else:
        st.info("PDFファイルをアップロードしてください。")

# Others ページ
elif page == page_list[3]:
    st.title("Others")
    st.write("This is a page for other analysis.")
