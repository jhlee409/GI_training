import streamlit as st
import requests
import json
import firebase_admin
from firebase_admin import credentials, storage
import datetime

st.set_page_config(page_title="GI_training", layout="wide")

# 제목 및 서브헤딩 설정
st.title("GI training programs")

# 설명 텍스트
with st.expander("**이 프로그램 사용 방법**"):
    st.write("* 로그인이 제대로 안되면 왼쪽 증례 페이지에 접근할 수 없습니다.")
    st.write("* 알려드린 id와 pw로 로그인 하신 후 왼쪽 sidebar에서 원하는 프로그램을 선택하면 그 페이지로 이동합니다.")
    st.write("* 이 프로그램은 울산의대 서울아산병원 이진혁과 의대 관계자 및 다른 서울아산병원 소화기 선생님들의 참여에 의해 제작되었습니다.")
st.divider()

# 사용자 인풋
email = st.text_input("Email")
password = st.text_input("Password", type="password")

# 로그인 버튼
if st.button("Login"):
    try:
        # Streamlit secret에서 Firebase API 키 가져오기
        api_key = st.secrets["FIREBASE_API_KEY"]
        request_ref = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"
        headers = {"Content-Type": "application/json"}
        data = json.dumps({"email": email, "password": password, "returnSecureToken": True})

        response = requests.post(request_ref, headers=headers, data=data)
        response_data = response.json()

        if response.status_code == 200:
            st.success(f"{email}님, 로그인에 성공하셨습니다. 이제 왼쪽의 메뉴를 이용하실 수 있습니다.")
            st.session_state['logged_in'] = True 
            st.session_state['user_email'] = email  # 이메일을 세션에 저장

            # 사용자 이메일과 접속 날짜 기록
            access_date = datetime.datetime.now().strftime("%Y-%m-%d")  # 현재 날짜 가져오기 (시간 제외)

            # 로그 내용을 문자열로 생성
            log_entry = f"Email: {email}, Access Date: {access_date}\n"

            # Firebase Storage에 로그 파일 업로드
            if not firebase_admin._apps:
                # Streamlit Secrets에서 Firebase 설정 정보 로드
                cred = credentials.Certificate({
                    "type": "service_account",
                    "project_id": st.secrets["project_id"],
                    "private_key_id": st.secrets["private_key_id"],
                    "private_key": st.secrets["private_key"].replace('\\n', '\n'),
                    "client_email": st.secrets["client_email"],
                    "client_id": st.secrets["client_id"],
                    "auth_uri": st.secrets["auth_uri"],
                    "token_uri": st.secrets["token_uri"],
                    "auth_provider_x509_cert_url": st.secrets["auth_provider_x509_cert_url"],
                    "client_x509_cert_url": st.secrets["client_x509_cert_url"],
                    "universe_domain": st.secrets["universe_domain"]
                })
                firebase_admin.initialize_app(cred)

            bucket = storage.bucket('amcgi-bulletin.appspot.com')  # Firebase Storage 버킷 참조
            log_blob = bucket.blob(f'logs/{email}_{access_date}.txt')  # 로그 파일 경로 설정
            log_blob.upload_from_string(log_entry, content_type='text/plain')  # 문자열로 업로드

        else:
            st.error(response_data["error"]["message"])
    except Exception as e:
        st.error("An error occurred: " + str(e))

# 로그 아웃 버튼
if "logged_in" in st.session_state and st.session_state['logged_in']:
    
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.success("로그아웃 되었습니다.")
        # 필요시 추가적인 세션 상태 초기화 코드
        # 예: del st.session_state['logged_in']