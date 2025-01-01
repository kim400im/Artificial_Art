import streamlit as st
from openai import OpenAI
import requests
import json
import time
from supabase import create_client, Client
from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 키 값 읽기
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")

supabase:Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(
    api_key=OPENAI_API_KEY
)

def send_to_gpt(data):
    """GPT에게 데이터를 보내고 응답을 반환합니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "In english, You are an artist. you are going to describe a illustration\
                that meets the user's demand. Don't over-imagine. Use specific wording(ex, light and shadow texture, flat colors, cell shading and ink lines). The style description needs to go first and last in the prompt(ex, retro anime, japanese illustration  ), or use the director or \
                artist's name related to the style(ex,Ghibli Studio, Hayao Miyazaki, Jeremy Geddes, Junji Ito ,naoko takeuchi,  ...), or specific style(ex: retro anime-> vhs effect,grainy texture, 80s anime, motion blur, realistic -> 4k, ). If it's animation or character,\
                 write simply, in 1~2 sentence.If the user wants a pretty girl, add 'in the style of guweiz'. Don't use korean. \
                 If it's realism, describe pose, layout, composition, add 4k. If the user seems to want retro anime, add --niji 5 at the end of the prompt. \
                 ##Example: 1. Cute little Chinese girl riding a big blue whale slowly swimming in the ocean, ancient China, comfortable, \
                 full body shot, flim stils, highly realistic.\
                 2.Japanese illustration, Retro illustration, Animation style, Light and shadow texture, Film style, \
                  cat girl, Magix, Neon Genesis Evangelion. "},
                {"role": "user", "content": f"Here is the user's demmand: {data}"}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def upscale(origin_task_id, index):
    # 업스케일 작업 요청
    url = "https://api.piapi.ai/api/v1/task"

    payload = json.dumps({
    "model": "midjourney",
    "task_type": "upscale",
    "input": {
        "origin_task_id": origin_task_id,
        "index":  str(index)
    },
    "config": {
        "service_mode": "",
        "webhook_config": {
            "endpoint": "",
            "secret": ""
        }
    }
    })
    headers = {
    'X-API-Key': PIAPI_API_KEY,
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)

    response_data = response.json()
    print(response_data)
    task_id = response_data.get("data", {}).get("task_id")
    print(task_id)
    return task_id


def create_img(prompt, ratio):
    url = "https://api.piapi.ai/api/v1/task"

    payload = json.dumps({
        "model": "midjourney",
        "task_type": "imagine",
        "input": {
            "prompt": prompt,
            "aspect_ratio": ratio,
            "process_mode": "fast",
            "skip_prompt_check": False,
            "bot_id": 0
        },
        "config": {
            "service_mode": "",
            "webhook_config": {
                "endpoint": "https://webhook.site/",
                "secret": "123456"
            }
        }
    })
    headers = {
        'x-api-key': PIAPI_API_KEY,
        'Content-Type': 'application/json'
    }

    response = requests.post(url, headers=headers, data=payload)
    response_data = response.json()
    task_id = response_data.get("data", {}).get("task_id")
    
    if task_id:
        print(f"Task created successfully! Task ID: {task_id}")
        return task_id
    else:
        print("Failed to create task.")
        return None

def check_task_status(task_id):
    url = f"https://api.piapi.ai/api/v1/task/{task_id}"
    headers = {
        'x-api-key': PIAPI_API_KEY
    }
    while True:
        response = requests.get(url, headers=headers)
        response_data = response.json()
        status = response_data.get("data", {}).get("status")
        
        if status == "completed":
            image_url = response_data.get("data", {}).get("output", {}).get("image_url")
            print(f"Image generation completed! URL: {image_url}")
            return image_url
        elif status in ("failed", "error"):
            print(f"Image generation failed. Status: {status}")
            return None
        else:
            print(f"Task status: {status}. Checking again in 5 seconds...")
            time.sleep(5)


def main():
    st.title("내 그림 그리기:magic_wand:")
    st.write("설문에 참여해 주세요!")


    # 설문조사 질문
    style = st.text_input("원하는 스타일의 그림에 대해 설명해주세요(ex. 지브리 영화):")
    object = st.text_area("그리고 싶은 대상에 대해 설명해주세요(ex. 교복 입은 소녀):")
    ratio = st.radio("이미지 비율을 선택하세요:", ("16:9", "1:1"))


    # 세션 상태 초기화
    if "review_submitted" not in st.session_state:
        st.session_state.review_submitted = False
    if "task_id" not in st.session_state:
        st.session_state.task_id = None
    if "image_url" not in st.session_state:
        st.session_state.image_url = None
    if "selected_index" not in st.session_state:
        st.session_state.selected_index = None
    if "upscaled_image_url" not in st.session_state:
        st.session_state.upscaled_image_url = None
    if "row_id" not in st.session_state:
        st.session_state.row_id = None


    # 데이터 제출
    if st.button("제출"):
        if style and object:
                st.session_state.review_submitted = False
                st.session_state.image_url=False
                survey_data = {"style": style, "object": object}
                st.write("제출 완료!")
                with st.spinner("데이터를 분석 중입니다. 잠시만 기다려주세요... 30초에서 1분 정도 걸립니다"):
                    gpt_response = send_to_gpt(survey_data)
                    task_id = create_img(gpt_response, ratio)
                    if task_id:
                        st.session_state.task_id=task_id
                        st.session_state.image_url = check_task_status(task_id)
                        data = {
                        "style": style,
                        "object": object,
                        "ratio":ratio,
                        "gpt_prompt": gpt_response,
                        "img_url": st.session_state.image_url
                    }

                        response = supabase.table("image_user").insert(data).execute()
                        print("response", response.data[0]["id"])
                        if response.data:
                            st.session_state.row_id = response.data[0]["id"]

    # 이미지 출력 및 버튼 표시
    if st.session_state.image_url:
        st.image(st.session_state.image_url, caption="Image from URL", use_column_width=True)
        # st.title("제일 만족스러운 이미지를 골라주세요! ")


    if st.session_state.image_url and not st.session_state.review_submitted:
        st.markdown("<h3 style='font-size:20px;'>이미지를 업스케일링 하시려면면, 리뷰 작성해주세요! (모든 항목이 필수는 아닙니다.)</h3>", unsafe_allow_html=True)
        satisfaction = st.radio("이미지에 만족하셨나요?", ("네", "아니요"))
        satisfaction = satisfaction == "네"
        rating = st.slider("평점을 입력해주세요 (1~5):", 1, 5, 3)
        review = st.text_area("별로였던 점을 입력해주세요:")
        # will_buy_goods = st.radio("굿즈 구매 의향이 있습니까?", ("네", "아니요"))
        # will_buy_goods = will_buy_goods == "네"
        use_site = st.radio("정식 웹사이트가 나온다면 이용하시겠습니까?", ("네", "아니요"))
        use_site = use_site == "네"
        email = st.text_input("이메일 주소를 입력해주세요 (선택 사항):")

        if st.button("리뷰 제출"):
            review_data = {
                "satisfaction": satisfaction,
                "rating": rating,
                "review": review,
                # "willingness_to_buy_goods": will_buy_goods,
                "email": email or None,
                "use_site": use_site,
            }
            response = supabase.table("image_user").update(review_data).eq("id", st.session_state.row_id).execute()
            if response.data:
                st.session_state.review_submitted = True
                st.rerun() 
                st.success("리뷰가 제출되었습니다. 감사합니다!")

    # 업스케일링 UI
    if st.session_state.review_submitted:
        st.write("업스케일할 이미지를 선택해주세요:")
        cols = st.columns(2)
        with cols[0]:
            if st.button("왼쪽 위"):
                st.session_state.selected_index = 1
        with cols[1]:
            if st.button("오른쪽 위"):
                st.session_state.selected_index = 2
        cols = st.columns(2)
        with cols[0]:
            if st.button("왼쪽 아래"):
                st.session_state.selected_index = 3
        with cols[1]:
            if st.button("오른쪽 아래"):
                st.session_state.selected_index = 4

    # 업스케일링 작업 수행
    if st.session_state.selected_index is not None:
        if not st.session_state.upscaled_image_url:
            with st.spinner("업스케일 작업 진행 중..."):
                task_id_upscale = upscale(st.session_state.task_id, st.session_state.selected_index)
                st.session_state.upscaled_image_url = check_task_status(task_id_upscale)

        if st.session_state.upscaled_image_url:
            st.image(st.session_state.upscaled_image_url, caption="Upscaled Image", use_column_width=True)
            updates = {"upscaled_img_url": st.session_state.upscaled_image_url}
            supabase.table("image_user").update(updates).eq("id", st.session_state.row_id).execute()
            st.success("업스케일 작업이 완료되었습니다!")


if __name__ == "__main__":
    main()