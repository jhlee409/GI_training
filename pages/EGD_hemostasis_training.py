import streamlit as st
import time
from PIL import Image
import docx
import io
from openai import OpenAI
import firebase_admin
from firebase_admin import credentials, storage

# 동영상 재생을 위한 라이브러리 추가
import os
import tempfile

# Set page to wide mode
st.set_page_config(page_title="EGD_Hemostasis_training", layout="wide")

if st.session_state.get('logged_in'):

    # Initialize prompt variable
    prompt = ""      

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

    client = OpenAI()

    # Display Form Title
    st.subheader("EGD_Dx_training")
    with st.expander(" 필독!!! 먼저 여기를 눌러 사용방법을 확인하세요."):
        st.write("- 가장 먼저 왼쪽 sidebar에서 F1용인지 F2용인지를 선택합니다.")
        st.write("- 그 아래에서 EGD 사진과 case instruction 파일을 차례로 선택해서 업로드 하세요. 동일한 이름의 png 파일과 docx 파일을 선택해야 합니다.")
        st.write("- '준비가 되었으면 아무 키나 입력한 후 엔터를 눌러 주세요'라고 나오면, 아무 키나 누르고, 엔터를 누른 후 기다립니다.")
        st.write("- 잠시 후에 문제에 따라 질문이나 질문 없는 설명이 나옵니다. 나오는 문장에 따라 진행하면됩니다.")
        st.write("- 그 증례에 대한 학습의 마지막은 '이 증례의 최종진단은 000입니다.'로 종결됩니다.")
        st.write("- 한 증례가 끝나고 다음 증례로 넘어가시려면, 먼저 왼쪽의 '초기화' 버튼을 선택하여 초기화 하고, 처음 과정부터 다시 시작하시면 됩니다.")
        st.write("- 각 단계마다 반드시 '열일 중' 스핀이 멈출 때까지 기다리세요. 스핀 돌고있는 도중에 다른 버튼 누르면 오류납니다.")
        st.write("- 얘가 융통성이 없습니다. 너무 짧은 대답(예 n)을 넣거나, 빙빙 돌려서 대답하거나, 지시 대명사(거시기)를 많이 쓰면 잘 못알아 듣습니다.")
        
    # Firebase에서 이미지를 다운로드하고 PIL 이미지 객체로 열기
    def download_and_open_image(bucket_name, file_path):
        bucket = storage.bucket(bucket_name)
        blob = bucket.blob(file_path)
        # BytesIO 객체를 사용하여 메모리에서 이미지를 직접 열기
        image_stream = io.BytesIO()
        blob.download_to_file(image_stream)
        image_stream.seek(0)
        return Image.open(image_stream)

    # Function to list files in a specific directory in Firebase Storage
    def png_list_files(bucket_name, directory):
        bucket = storage.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=directory)
        file_names = []
        for blob in blobs:
            # Extracting file name from the path and adding to the list
            file_name = blob.name[len(directory):]  # Remove directory path from file name
            if file_name:  # Check to avoid adding empty strings (in case of directories)
                file_names.append(file_name)
        return file_names
    
    # F1 or F2 selection
    folder_selection = st.sidebar.radio("Select Folder", ["초기화", "esophagus", "stomach_1", "stomach_2", "duodenum"])

    if folder_selection == "초기화":
        directory_images = "EGD_Hemostasis_training/Default/images/"
        directory_instructions = "EGD_Hemostasis_training/Default/instructions/"
        directory_thumbnails = "EGD_Hemostasis_training/Default/thumbnails/"  # 추가: 초기화 시 비디오 디렉토리 설정
        st.session_state.prompt = ""
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.session_state['messages'] = []
        #st.experimental_rerun()
    
    elif folder_selection == "esophagus":
        directory_images = "EGD_Hemostasis_training/esophagus/images/"
        directory_instructions = "EGD_Hemostasis_training/esophagus/instructions/"
        directory_thumbnails = "EGD_Hemostasis_training/esophagus/thumbnails/"  # 추가: esophagus 폴더의 비디오 디렉토리
    elif folder_selection == "stomach_1":
        directory_images = "EGD_Hemostasis_training/stomach_1/images/"
        directory_instructions = "EGD_Hemostasis_training/stomach_1/instructions/"
        directory_thumbnails = "EGD_Hemostasis_training/stomach_1/thumbnails/"  # 추가: stomach_1 폴더의 비디오 디렉토리
    elif folder_selection == "stomach_2":
        directory_images = "EGD_Hemostasis_training/stomach_2/images/"
        directory_instructions = "EGD_Hemostasis_training/stomach_2/instructions/"
        directory_thumnbails = "EGD_Hemostasis_training/stomach_2/thumbnails/"  # 추가: stomach_2 폴더의 비디오 디렉토리
    else:
        directory_images = "EGD_Hemostasis_training/duodenum/images/"
        directory_instructions = "EGD_Hemostasis_training/duodenum/instructions/"
        directory_thumbnails = "EGD_Hemostasis_training/duodenum/thumbnails/"  # 추가: duodenum 폴더의 비디오 디렉토리

    st.sidebar.divider()

    # List and select PNG files
    file_list_images = png_list_files('amcgi-bulletin.appspot.com', directory_images)
    selected_image_file = st.sidebar.selectbox(f"증례를 선택하세요.", file_list_images)

    if selected_image_file:
        selected_image_path = directory_images + selected_image_file
        image = download_and_open_image('amcgi-bulletin.appspot.com', selected_image_path)
        
        # Open the image to check its dimensions
        # The 'image' variable already contains a PIL Image object, so you don't need to open it again
        width, height = image.size
        
        # Determine the display width based on the width-height ratio
        display_width = 400 # if width >= 1.6 * height else 700
        
        st.image(image, width=display_width)

    # Function to list files in a specific directory in Firebase Storage
    def list_files(bucket_name, directory):
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
    
    # List and select DOCX files
    file_list_instructions = list_files('amcgi-bulletin.appspot.com', directory_instructions)
    selected_instruction_file = st.sidebar.selectbox(f"case instruction 파일을 선택하세요.", file_list_instructions)

    # Read and display the content of the selected DOCX file
    if selected_instruction_file:
        full_path = directory_instructions + selected_instruction_file
        prompt = read_docx_file('amcgi-bulletin.appspot.com', full_path)
        st.session_state['prompt'] = prompt
        #st.text(prompt)  # Display the content of the docx file as text

    # 추가: 동영상 파일 리스트 가져오기
    video_list = list_files('amcgi-bulletin.appspot.com', directory_thumbnails)

    # 추가: 동영상 파일 선택 드롭다운 메뉴
    selected_video = st.sidebar.selectbox("동영상 선택", video_list)
    
    if selected_video:
        video_path = directory_thumbnails + selected_video
        
        # Firebase Storage에서 동영상 파일 다운로드
        bucket = storage.bucket('amcgi-bulletin.appspot.com')
        blob = bucket.blob(video_path)
        
        # 임시 파일 경로 생성
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            blob.download_to_file(temp_file)
            temp_file_path = temp_file.name
        
        # 동영상 재생
        video_file = open(temp_file_path, 'rb')
        video_bytes = video_file.read()
        st.video(video_bytes, format='video/mp4', start_time=0)
        
        # 임시 파일 삭제
        os.unlink(temp_file_path)

    # Manage thread id
    if 'thread_id' not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    thread_id = st.session_state.thread_id

    assistant_id = "asst_AyqS2LqfxPw2RwRV1sl1bGhd"

    # Get user input from chat nput
    user_input = st.chat_input("입력창입니다. 선생님의 message를 여기에 입력하고 엔터를 치세요")

    # 사용자 입력이 있을 경우, prompt를 user_input으로 설정
    if user_input:
        if user_input.strip():  # Check if user_input is not empty or whitespace
            prompt = user_input
        else:
            print("Please enter a non-empty prompt.")
            # Handle the case when user_input is empty or whitespace
            # You can prompt the user to enter a valid input or take appropriate action
    else:
        print("No user input provided.")
        # Handle the case when user_input is None or not provided
        # You can prompt the user to enter a valid input or take appropriate action

    if prompt:
        message = client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=prompt
        )

    #RUN을 돌리는 과정
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    with st.spinner('열일 중...'):
        #RUN이 completed 되었나 1초마다 체크
        while run.status != "completed":
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )

    #while문을 빠져나왔다는 것은 완료됐다는 것이니 메세지 불러오기
    messages = client.beta.threads.messages.list(
        thread_id=thread_id
    )

    #메세지 모두 불러오기
    thread_messages = client.beta.threads.messages.list(thread_id, order="asc")

    # 로그아웃 버튼 생성
    if st.sidebar.button('로그아웃'):
        st.session_state.logged_in = False
        st.experimental_rerun()  # 페이지를 새로고침하여 로그인 화면으로 돌아감

    for msg in thread_messages.data:
        # 메시지 내용 확인 및 필터링 조건 추가
        if msg.content and msg.content[0].text.value:
            content = msg.content[0].text.value
            # 필터링 조건: 내용이 비어있지 않고, '..', '...', '전체 지시 사항'을 포함하지 않는 경우에만 UI에 표시
            if content.strip() not in ['', '..', '...'] and '전체 지시 사항' not in content:
                with st.chat_message(msg.role):
                    st.write(content)
        
else:
    # 로그인이 되지 않은 경우, 로그인 페이지로 리디렉션 또는 메시지 표시
    st.error("로그인이 필요합니다.")