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

# @st.cache_data
# def open_image(file):
#     img = Image.open(file).convert("RGB")
#     return np.array(img)

# if not check_password():
#     st.stop()  # Do not continue if check_password is not True.


# ページ選択メニューをサイドバーに表示
st.sidebar.title("Navigation window")

pi = 3.14159265359
page_list = ["Home", "Patent", "Others"]
wafer_size_list = ["2 inch", "4 inch, 100 mm", "6 inch, 150 mm"]
plot_type_list = ["Line", "Histgram", "Scatter", "Contour", "3D"]
xrd_type_list = ["XRD 2θ-ω", "ω-Rocking Curve", "Others"]
om_type_list = ["Image Viewer", "Object Detection", "Others"]
lm_type_list = ["Defect Mapping", "Defect Image", "Others"]
margin = 1.1
OF = -0.93
cms = plt.cm.datad.keys()

page = st.sidebar.selectbox("Select measurements for analysis.", page_list)
wafer_size = st.sidebar.selectbox("Select wafer size", wafer_size_list)
r = {"2 inch": 25.0, "4 inch, 100 mm": 50.0, "6 inch, 150 mm": 75.0}.get(wafer_size, 25.0)

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
    df = pd.read_csv(file_thick, encoding='utf-8', encoding_errors='ignore') if file_thick is not None else pd.DataFrame()
    st.write(df)

# Others
elif page==page_list[2]:
    st.title(page_list[2])
    st.write("This is a page for other analysis.")