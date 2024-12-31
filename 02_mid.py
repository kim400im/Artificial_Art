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
                that meets the user's demand. Don't over-imagine. Don't use abstract words, use specific wording. The style description needs to go first and last in the prompt, or use the director or \
                artist's name related to the style(ex,Hayao Miyazaki,Jeremy Geddes, Junji Ito ,naoko takeuchi ...), or specific style(ex: retro anime-> vhs effect,grainy texture, 80s anime, motion blur, realistic). If it's animation or character,\
                 write simply, in 1~2 sentence.If the user wants a pretty girl, add 'in the style of guweiz'. If there is a proper noun that you don't know, abstract it. (ex: 짱구 -> Japanese illustration) \
                 If it's realism, describe pose, layout, composition. If the user seems to want retro anime, add --niji 5 at the end of the prompt. \
                 ##Example: 1. Cute little Chinese girl riding a big blue whale slowly swimming in the ocean, ancient China, comfortable, \
                 full body shot, flim stils, highly realistic.\
                 2.Japanese illustration, Retro illustration, Animation style, Light and shadow texture, Film style, \
                  cat girl, Magix, Neon Genesis Evangelion. \
                  3. The image of a man shrouded in a shroud seems to merge with the air around him, high contrast \
                  between the dark background and the bright, glowing texture of the material to create a sense of emergence or transformation,\
                   monochrome shades to enhance the mysterious and tense atmosphere,high realism"},
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
    
    # Initialize session state for image and selected index
    if "selected_index" not in st.session_state:
        st.session_state.selected_index = None
    if "image_url" not in st.session_state:
        st.session_state.image_url = None
    if "upscaled_image_url" not in st.session_state:
        st.session_state.upscaled_image_url = None
    if "task_id" not in st.session_state:
        st.session_state.task_id = None

    # 데이터 제출
    if st.button("제출"):
        if style and object:
            survey_data = {
                "style": style,
                "object": object,
            }
            st.write("제출 완료!")

        # Spinner 시작
            with st.spinner("데이터를 분석 중입니다. 잠시만 기다려주세요... 30초에서 1분 정도 걸립니다"):
                # GPT에게 데이터 전달
                gpt_response = send_to_gpt(survey_data)
                # st.subheader("GPT 응답:")
                # st.write(gpt_response)

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
        st.title("제일 만족스러운 이미지를 골라주세요! ")
        
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
        st.write(f"You selected index: {st.session_state.selected_index}")
        if "upscaled_image_url" not in st.session_state or not st.session_state.upscaled_image_url:
            with st.spinner("업스케일링 작업을 진행 중입니다. 잠시만 기다려주세요..."):
                task_id_upscale = upscale(st.session_state.task_id, st.session_state.selected_index)
                # 작업 상태 확인 루프
                for _ in range(20):  # 최대 20회 (타임아웃 설정)
                    st.session_state.upscaled_image_url = check_task_status(task_id_upscale)
                    if st.session_state.upscaled_image_url:
                        break
                    time.sleep(1)  # 1초 간격으로 상태 확인
                
                # st.session_state.upscaled_image_url = check_task_status(task_id_upscale)
                if not st.session_state.upscaled_image_url:
                    st.error("업스케일링 작업이 완료되지 않았습니다. 다시 시도해주세요.")
        if st.session_state.upscaled_image_url:
            st.image(st.session_state.upscaled_image_url, caption="Upscaled Image", use_column_width=True)
            updates = {
            "upscaled_img_url": st.session_state.upscaled_image_url
        }

            response = supabase.table("image_user").update(updates).eq("id", st.session_state.row_id).execute()
    
    if st.session_state.image_url or st.session_state.upscaled_image_url:
        st.header("리뷰를 작성해주세요!")
        satisfaction = st.radio("이미지에 만족하셨나요?", ("네", "아니요"))
        satisfaction = True if satisfaction == "네" else False
        rating = st.slider("평점을 입력해주세요 (1~5):", min_value=1, max_value=5, step=1)
        review=st.text_area("더 나아질 수 있는 점을 입력해주시면 앱 발전에 큰 도움이 될 것입니다! ex) 이미지 사이즈 선택 가능 기능 등등등")
        will_buy_goods = st.radio("제작된 이미지를 바탕으로 굿즈가 나온다면 구매하시겠습니까?", ("네", "아니요"))
        will_buy_goods_bool = True if will_buy_goods == "네" else False
        email = st.text_input("더 많은 소식을 알고 싶으시면,이메일 주소를 입력해주세요:")

        if st.button("리뷰 제출"):
            if email:
                review_data = {
                    "satisfaction": satisfaction,
                    "rating": rating,
                    "review": review,
                    "willingness_to_buy_goods": will_buy_goods_bool,
                    "email": email
                }
                response = supabase.table("image_user").update(review_data).eq("id", st.session_state.row_id).execute()
                if response.data:
                    st.success("리뷰가 제출되었습니다. 감사합니다!")
            else:
                st.error("이메일 주소를 입력해주세요.")


if __name__ == "__main__":
    main()