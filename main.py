import streamlit as st
import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objs as go
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from datetime import datetime, timedelta
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
    file_thick = st.file_uploader("Upload a CSV file", type='csv')
    if file_thick is not None:
        df = pd.read_csv(file_thick, encoding='utf-8', encoding_errors='ignore')
        target_date_col = st.sidebar.selectbox("Select date column", df.columns.to_list(), index=2)
        df[target_date_col] = pd.to_datetime(df[target_date_col])
        df['年'] = df[target_date_col].dt.year.astype('int')
        df['出願人/権利者'] = df['出願人/権利者'].astype('str')

        # st.write(df['出願人/権利者'].unique())

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

        # df_applicant = pd.DataFrame(applicant_list, columns=['出願人/権利者'])
        # df_applicant['件数'] = 0

        # bar_applicant = st.progress(0, text='Now progress...')

        with st.spinner('Loading...'):
            # for i, applicant in enumerate(applicant_list):
            #     df_applicant.loc[df_applicant['出願人/権利者']==applicant, '件数'] = df_date[df_date['出願人/権利者'].str.contains(applicant)]['文献番号'].count()
            #     for stage in df_date['ステージ'].unique():
            #         df_applicant.loc[df_applicant['出願人/権利者']==applicant, f'ステージ_{stage}'] = df_date[(df_date['出願人/権利者'].str.contains(applicant))&(df_date['ステージ']==stage)]['文献番号'].count()
            #     for year in range(min_year,max_year):
            #         df_applicant.loc[df_applicant['出願人/権利者']==applicant, str(year)+'年'] = df_date[(df_date['出願人/権利者'].str.contains(applicant))&(df_date['年']==year)]['文献番号'].count()
            #     bar_applicant.progress(i/len(applicant_list), text=f'Now progress...{i}/{len(applicant_list)}')
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

        # データの表示
        # st.write(df_applicant)
        applicant = st.sidebar.selectbox("Select applicant", df_applicant['出願人/権利者'].unique(), index=0)

        # bar_applicant.empty()

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

            # データの可視化
            st.header("Visualization")
            with st.spinner('Visualizing...'):
                fig2 = go.Figure()
                fig2.add_trace(
                    go.Bar(
                        x=df_applicant['件数'].values[:50], 
                        y=df_applicant['出願人/権利者'].values[:50], 
                        name='Patents per Applicant', 
                        orientation='h'
                        ))
                fig2.update_layout(
                    title='Patents per Applicant',
                    height=1200,
                    width=900,
                    xaxis_title='Counts',
                    yaxis_title='Applicants',
                    yaxis=dict(autorange="reversed")  # 件数が多い順に上から表示
                    )
                st.plotly_chart(fig2)
            
            # st.write(df_year_grouped)
            # st.write(df_year_grouped[df_year_grouped['出願人/権利者'].str.contains(applicant)].T)
            # st.write(len(df_year_grouped.columns.to_list()[1:]))
            # st.write(len(df_year_grouped[df_year_grouped['出願人/権利者'].str.contains(applicant)].T.iloc[:,0].to_list()[1:]))

            with st.spinner("Visualizing..."):
                fig3 = go.Figure()
                fig3.add_trace(
                    go.Scatter(
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
    file_thick = st.file_uploader("Upload a PDF file", type='pdf')


# Others
elif page==page_list[3]:
    st.title(page_list[3])
    st.write("This is a page for other analysis.")