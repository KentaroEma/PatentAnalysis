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
analysis_list = ["Overview", "Aplicant", "Others"]
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

        # pandas.Timestamp → datetime.date に変換
        min_date = df[target_date_col].min().date()
        max_date = df[target_date_col].max().date()

        # カレンダー入力
        start_date, end_date = st.sidebar.date_input(
        "Select date range",
        [min_date, max_date],  # デフォルト値（最小日付～最大日付）
        min_value=min_date,
        max_value=max_date
        )
        
        # min_date = st.sidebar.date_input("Min date", min_date)
        # max_date = st.sidebar.date_input("Max date", max_date)

        df_date = df[(df[target_date_col]>=start_date)&(df[target_date_col]<=end_date)]
        # df_date = df[(df[target_date_col]>=range_date[0])&(df[target_date_col]<=range_date[1])]

        st.write(df_date)
    

# Claim
elif page==page_list[2]:
    st.title(page_list[2])
    target_col = 'Claim'
    file_thick = st.file_uploader("Upload a PDF file", type='pdf')


# Others
elif page==page_list[3]:
    st.title(page_list[3])
    st.write("This is a page for other analysis.")