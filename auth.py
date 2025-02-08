# auth.py

import os
import hmac
import streamlit as st
from datetime import datetime, timedelta

# セッションの有効期限を分単位で設定
SESSION_EXPIRY_MINUTES = 60

def check_password():
    """
    パスワードが正しいかどうかを確認し、セッションを管理する関数。
    
    Returns:
        bool: パスワードが正しければTrue、間違っていればFalse
    """
    def password_entered():
        """
        ユーザーが入力したパスワードが正しいかどうかをチェックする内部関数。
        """
        # 環境変数に保存されたパスワードと比較
        if hmac.compare_digest(st.session_state["password_input"], os.environ["LOGIN_PASSWORD"]):
            st.session_state["password_correct"] = True
            st.session_state["session_expiry"] = datetime.now() + timedelta(minutes=SESSION_EXPIRY_MINUTES)
            del st.session_state["password_input"]  # セッションからパスワードを削除
        else:
            st.session_state["password_correct"] = False

    # セッションが有効かどうかを確認
    if st.session_state.get("password_correct", False):
        expiry_time = st.session_state.get("session_expiry", None)
        if expiry_time and datetime.now() < expiry_time:
            return True
        else:
            # セッションの有効期限が切れた場合、再認証を要求
            st.session_state["password_correct"] = False
            st.session_state["session_expiry"] = None

    # パスワード入力欄を表示
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password_input"
    )

    # 認証に失敗した場合はエラーメッセージを表示
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect or session expired")
    return False


