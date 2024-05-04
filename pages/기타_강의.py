import streamlit as st
import os
from PIL import Image
import docx
import io
import firebase_admin
from firebase_admin import credentials, storage
from datetime import datetime, timedelta

# Set page to wide mode
st.set_page_config(page_title="EGD 강의", layout="wide")

if st.session_state.get('logged_in'):     

    # Check if Firebase app has already been initialized
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

    # Display Form Title
    st.subheader("EGD 기타 강의 모음")
    with st.expander(" 필독!!! 먼저 여기를 눌러 사용방법을 확인하세요."):
        st.write("- 이 EGD 기타 강의 모음은 상부 지혈술 외의 주제에 대한 강의 동영상 모음입니다. EGD 지혈술 강의를 보시려면 EGD hemostasis training으로 이동하셔서 Hemostasis 강의 항목으로 이동하세요.")
        st.write("- 가장 먼저 왼쪽 sidebar에서 default는 '초기화'입니다. 잠시 기다렸다가 보고자 하는 주제의 제목을 가진 강의 한 가지를 선택합니다.")
        st.write("- 강의 첫 화면이 나타나면 화면을 클릭해서 시청하세요.")
        st.write("- 전체 화면을 보실 수 있습니다. 화면 왼쪽 아래 전체 화면 버튼 누르세요.")
        st.write("- 다음 강의로 넘어가려면 다시 '초기화'를 선택하여 같은 과정을 진행합니다.")
          
    # Function to list files in a specific directory in Firebase Storage
    def pre_videos_list_files(bucket_name, directory):
        bucket = storage.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=directory)
        file_names = []
        for blob in blobs:
            # Extracting file name from the path and adding to the list
            file_name = blob.name[len(directory):]  # Remove directory path from file name
            if file_name:  # Check to avoid adding empty strings (in case of directories)
                file_names.append(file_name)
        return file_names
    
    # Function to read file content from Firebase Storage
    def read_docx_file(bucket_name, file_name):
        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(file_name)
        
        # Download the file to a temporary location
        temp_file_path = "/tmp/tempfile.docx"
        blob.download_to_filename(temp_file_path)
        
        # Read the content of the DOCX file
        doc = docx.Document(temp_file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        
        # Join the text into a single string
        return '\n'.join(full_text)
    
    # esophagus or stomach selection
    folder_selection = st.sidebar.radio("선택 버튼", ["초기화", "Hemostasis 강의", "esophagus", "stomach", "duodenum"])
    
    directory_videos = "EGD_Hemostasis_training/videos/"

    if folder_selection == "초기화":
        directory_pre_videos = "EGD_Hemostasis_training/default/pre_videos/"
        directory_instructions = "EGD_Hemostasis_training/default/instructions/"
    if folder_selection == "Hemostasis 강의":
        directory_pre_videos = "EGD_Hemostasis_training/lecture/video/"
        directory_instructions = "EGD_Hemostasis_training/lecture/instruction/"    
    elif folder_selection == "esophagus":
        directory_pre_videos = "EGD_Hemostasis_training/esophagus/pre_videos/"
        directory_instructions = "EGD_Hemostasis_training/esophagus/instructions/"
    elif folder_selection == "stomach":
        directory_pre_videos = "EGD_Hemostasis_training/stomach/pre_videos/"
        directory_instructions = "EGD_Hemostasis_training/stomach/instructions/"
    else:
        directory_pre_videos = "EGD_Hemostasis_training/duodenum/pre_videos/"
        directory_instructions = "EGD_Hemostasis_training/duodenum/instructions/"

    st.sidebar.divider()

    # 선택한 동영상 파일을 세션 상태에 저장
    if 'selected_pre_videos_file' not in st.session_state:
        st.session_state.selected_pre_videos_file = None


    # List and select PNG files
    file_list_pre_videos = pre_videos_list_files('amcgi-bulletin.appspot.com', directory_pre_videos)
    selected_pre_videos_file = st.sidebar.selectbox(f"pre_video를 선택하세요.", file_list_pre_videos)

    # 동영상 플레이어를 렌더링할 컨테이너 생성
    pre_video_container = st.container()
    video_player_container = st.container()

    if selected_pre_videos_file:
        if selected_pre_videos_file != st.session_state.get('selected_pre_videos_file', ''):
            st.session_state.selected_pre_videos_file = selected_pre_videos_file
            selected_pre_videos_path = directory_pre_videos + selected_pre_videos_file
            
            # Firebase Storage 참조 생성
            bucket = storage.bucket('amcgi-bulletin.appspot.com')
            blob = bucket.blob(selected_pre_videos_path)
            expiration_time = datetime.utcnow() + timedelta(seconds=1600)
            pre_video_url = blob.generate_signed_url(expiration=expiration_time, method='GET')
            st.session_state.pre_video_url = pre_video_url
            
            # 선택한 pre_video와 같은 이름의 docx 파일 찾기
            instruction_file_name = os.path.splitext(selected_pre_videos_file)[0] + '.docx'
            selected_instruction_file = directory_instructions + instruction_file_name
                       
            # 선택한 pre_video와 같은 이름의 mp4 파일 찾기
            video_name = os.path.splitext(selected_pre_videos_file)[0] + '_2' + '.mp4'
            selected_video_file = directory_videos + video_name
            st.session_state.selected_video_file = selected_video_file  # 세션 상태에 저장
            
            # Read and display the content of the selected DOCX file
            if selected_instruction_file:
                full_path = selected_instruction_file
                prompt = read_docx_file('amcgi-bulletin.appspot.com', full_path)
                prompt_lines = prompt.split('\n')  # 내용을 줄 바꿈 문자로 분리
                prompt_markdown = '\n'.join(prompt_lines)  # 분리된 내용을 다시 합치면서 줄 바꿈 적용
                st.markdown(prompt_markdown)
            
            # 이전 동영상 플레이어 지우기
            pre_video_container.empty()
            video_player_container.empty()
            
        # 새로운 동영상 플레이어 렌더링
        with pre_video_container:           
            video_html = f'''
                <video id="video_player" width="350" controls controlsList="nodownload">
                    <source src="{st.session_state.pre_video_url}" type="video/mp4">
                </video>
                <script>
                    var video_player = document.getElementById('video_player');
                    video_player.addEventListener('contextmenu', function(e) {{
                        e.preventDefault();
                    }});
                </script>
            '''
            st.components.v1.html(video_html, height=350)
            
            instruction_file_name = os.path.splitext(selected_pre_videos_file)[0] + '.docx'
            selected_instruction_file = directory_instructions + instruction_file_name

        # '진행' 버튼 추가
        if st.sidebar.button('진행'):
            if st.session_state.get('selected_video_file'):
                # Firebase Storage 참조 생성
                bucket = storage.bucket('amcgi-bulletin.appspot.com')
                blob = bucket.blob(st.session_state.selected_video_file)
                expiration_time = datetime.utcnow() + timedelta(seconds=1600)
                video_url = blob.generate_signed_url(expiration=expiration_time, method='GET')

                # 비디오 플레이어 삽입
                video_html = f'''
                <video id="video_player" width="600" controls controlsList="nodownload">
                    <source src="{video_url}" type="video/mp4">
                </video>
                <script>
                var video_player = document.getElementById('video_player');
                video_player.addEventListener('contextmenu', function(e) {{
                    e.preventDefault();
                }});
                </script>
                '''
                with video_player_container:
                    st.components.v1.html(video_html, height=600)

            st.sidebar.divider()

            # 로그아웃 버튼 생성
            if st.sidebar.button('로그아웃'):
                st.session_state.logged_in = False
                st.experimental_rerun()  # 페이지를 새로고침하여 로그인 화면으로 돌아감

            if folder_selection == "초기화":
                st.empty()  # 동영상 플레이어 제거
else:
    # 로그인이 되지 않은 경우, 로그인 페이지로 리디렉션 또는 메시지 표시
    st.error("로그인이 필요합니다.") 