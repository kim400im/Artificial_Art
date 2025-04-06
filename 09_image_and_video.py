# 영어로 된 버전 
import streamlit as st
from openai import OpenAI
import requests
import json
import time
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from typing import Optional, List, Union
import base64

# .env 파일 로드
load_dotenv()

# 환경 변수에서 키 값 읽기
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PIAPI_API_KEY = os.getenv("PIAPI_API_KEY")
VIDU_API_KEY = os.getenv("VIDU_API_KEY")

supabase:Client = create_client(SUPABASE_URL, SUPABASE_KEY)
client = OpenAI(
    api_key=OPENAI_API_KEY
)

def filter_inappropriate_content_gpt(data):
    """
    GPT를 사용하여 사용자의 입력 데이터를 검열합니다.

    Parameters:
        data (str): 사용자 입력 데이터.

    Returns:
        bool: True if inappropriate content is detected, otherwise False.
        str: 검열 결과 메시지.
    """
    try:
        # GPT 요청을 통해 부적절한 내용 검열
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a content moderation assistant. Analyze the user's input and determine if it contains inappropriate, offensive, or NSFW content. "
                        "Try to censor even inappropriate words that Midjourney can't draw. such as sexual elements, sexual clotings"
                        "Cigaratte and Tobacco is not subject for censorshhip. respond with Content approved"
                        "If it does, respond with 'Content flagged: [reason]'. If not, respond with 'Content approved'. "
                        "Use the following categories to flag content: hate speech, adult content, racism, sexism, or illegal activities."
                    )
                },
                {
                    "role": "user",
                    "content": f"Here is the user's input: {data}"
                }
            ]
        )

        gpt_response = response.choices[0].message.content.strip()

        if "Content flagged:" in gpt_response:
            # 부적절한 내용이 감지된 경우
            reason = gpt_response.split("Content flagged:")[1].strip()
            return True, f"unappropriate words: {reason}"
        else:
            # 내용이 적합한 경우
            return False, ""
    except Exception as e:
        return True, f"error during filtering: {e}"

def send_to_gpt(data):
    """GPT에게 데이터를 보내고 응답을 반환합니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "In English, create minimal prompts for Midjourney. Simply combine the user's style request and character/object description in english. Do not add extra details the user hasn't requested, must be in midjourney prompt style"},
                {"role": "user", "content": f"Here is the user's demmand: {data}"}
            ]
        )
        gpt_response = response.choices[0].message.content
        
        # 응답이 이미 "--niji"로 끝나는지 확인
        if "--niji" not in gpt_response:
            # niji 6 추가
            gpt_response = f"{gpt_response} --niji 6"
        
        return gpt_response
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
        try:
            response = requests.get(url, headers=headers)
            response_data = response.json()
            status = response_data.get("data", {}).get("status")
            
            if status == "completed":
                image_url = response_data.get("data", {}).get("output", {}).get("image_url")
                print(f"Image generation completed! URL: {image_url}")
                return image_url
            elif status in ("failed", "error"):
                error_message = response_data.get("data", {}).get("error", "알 수 없는 오류")
                print(f"Image generation failed. Status: {status}, Error: {error_message}")
                return None
            else:
                print(f"Task status: {status}. Checking again in 5 seconds...")
                time.sleep(5)
        except (requests.exceptions.JSONDecodeError, json.JSONDecodeError) as e:
            print(f"JSON parsing error: {e}")
            print(f"Response content: {response.text}")
            time.sleep(5)  # 잠시 기다린 후 다시 시도
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            time.sleep(5)  # 네트워크 문제 시 기다린 후 다시 시도
            
def translate_to_english(text):
    """어떤 언어든 영어로 번역합니다."""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a translator. Translate any text to English simply and accurately."},
                {"role": "user", "content": f"Translate this to English: {text}"}
            ]
        )
        english_text = response.choices[0].message.content.strip()
        print(f"Original: {text}")
        print(f"Translated: {english_text}")
        return english_text
    except Exception as e:
        print(f"Translation error: {e}")
        return text  # 번역 실패 시 원본 반환

def create_action_img(action_prompt, character_img_url, original_ratio):
    """
    기존 캐릭터 이미지를 참조하여 새로운 동작을 하는 이미지를 생성합니다.
    """
    url = "https://api.piapi.ai/api/v1/task"
    
    # 프롬프트를 항상 영어로 번역
    english_prompt = translate_to_english(action_prompt)
    
    # --cref 파라미터를 프롬프트에 추가
    full_prompt = f"{english_prompt} --cref {character_img_url} --niji 6"

    payload = json.dumps({
        "model": "midjourney",
        "task_type": "imagine",
        "input": {
            "prompt": full_prompt,
            "aspect_ratio": original_ratio,
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
        print(f"Action task created successfully! Task ID: {task_id}")
        return task_id
    else:
        print("Failed to create action task.")
        return None

class ViduAI:
    """A client for the Vidu AI Image to Video API."""
    
    BASE_URL = "https://api.vidu.com/ent/v2"
    
    def __init__(self, api_key: str):
        """Initialize the Vidu AI client."""
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {api_key}"
        }
    
    def image_to_video(self, 
                      images: Union[List[str], str],
                      model: str = "vidu2.0",
                      prompt: Optional[str] = None,
                      duration: int = 4,
                      seed: Optional[int] = None,
                      resolution: str = "720p",
                      movement_amplitude: str = "auto",
                      callback_url: Optional[str] = None,
                      wait_for_completion: bool = False,
                      polling_interval: int = 5,
                      max_polling_attempts: int = 60) -> dict:
        """Convert an image to a video using Vidu AI."""
        # Handle single image
        if isinstance(images, str):
            images = [images]
            
        # Prepare payload
        payload = {
            "model": model,
            "images": images,
        }
        
        # Add optional parameters if provided
        if prompt:
            payload["prompt"] = prompt
        if duration:
            payload["duration"] = duration
        if seed is not None:
            payload["seed"] = seed
        if resolution:
            payload["resolution"] = resolution
        if movement_amplitude:
            payload["movement_amplitude"] = movement_amplitude
        if callback_url:
            payload["callback_url"] = callback_url
            
        # Make the request
        response = requests.post(
            f"{self.BASE_URL}/img2video",
            headers=self.headers,
            json=payload
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Get the response data
        result = response.json()
        
        # If wait_for_completion is True, poll until the task is complete
        if wait_for_completion:
            task_id = result.get("task_id")
            if not task_id:
                raise ValueError("No task_id in response")
                
            attempts = 0
            while attempts < max_polling_attempts:
                status = self.get_task_status(task_id)
                state = status.get("state")
                
                if state == "success":
                    return status
                elif state == "failed":
                    raise Exception(f"Task failed: {status.get('err_code', 'Unknown error')}")
                elif state in ["created", "queueing", "processing"]:
                    time.sleep(polling_interval)
                    attempts += 1
                else:
                    raise Exception(f"Unknown state: {state}")
                    
            raise TimeoutError(f"Task did not complete after {max_polling_attempts * polling_interval} seconds")
        
        return result
    
    def get_task_status(self, task_id: str) -> dict:
        """Get the status of a task."""
        response = requests.get(
            f"{self.BASE_URL}/tasks/{task_id}/creations",
            headers=self.headers
        )
        
        # Check for errors
        response.raise_for_status()
        
        return response.json()

def main():
    st.title("Create Your Animaion! ")
    # st.write("This is a demo version of the character creation tool. Please provide your feedback to help us improve!")
    # 상세 설명 추가
    st.markdown("""
    ## Welcome to our Animation Creation Tool!
    
    **This service is completely FREE!** This is a testing page to gather user feedback and will only be available for until May 2025. The UI and features are minimally implemented, so please understand this limitation.
    
    With this tool, you can:
    * Create your own character
    * Generate different poses while maintaining character consistency
    * Create videos from your character images
    
    To upscale your images, you'll need to complete a short survey when prompted.
    
    If you encounter any errors, please try refreshing the page. If issues persist, feel free to DM me at **@sol2.4studio**.
    
    We appreciate your feedback to help us improve!
    """)

    # 설문조사 질문
    # style = st.text_input("원하는 스타일의 그림에 대해 설명해주세요(ex. 지브리 영화):")
    # object = st.text_area("그리고 싶은 대상에 대해 설명해주세요(ex. 교복 입은 소녀):")
    # ratio = st.radio("이미지 비율을 선택하세요:", ("16:9", "1:1"))


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
    if "action_image_url" not in st.session_state:
        st.session_state.action_image_url = None
    if "action_task_id" not in st.session_state:
        st.session_state.action_task_id = None
    if "action_selected_index" not in st.session_state:
        st.session_state.action_selected_index = None
    if "action_upscaled_image_url" not in st.session_state:
        st.session_state.action_upscaled_image_url = None
    if "character_created" not in st.session_state:
        st.session_state.character_created = False
    if "video_creating" not in st.session_state:
        st.session_state.video_creating = False
    if "video_prompt" not in st.session_state:
        st.session_state.video_prompt = ""
    if "video_url" not in st.session_state:
        st.session_state.video_url = None
    if "video_task_id" not in st.session_state:
        st.session_state.video_task_id = None
    if "action_video_creating" not in st.session_state:
        st.session_state.action_video_creating = False
    if "action_video_prompt" not in st.session_state:
        st.session_state.action_video_prompt = ""
    if "action_video_url" not in st.session_state:
        st.session_state.action_video_url = None
    if "video_id" not in st.session_state:
        st.session_state.video_id = None
    if "action_video_id" not in st.session_state:
        st.session_state.action_video_id = None


    # 캐릭터 생성 단계
    if not st.session_state.character_created:
        # 설문조사 질문
        style = st.text_input("Describe the art style you want (e.g., cute anime style, disney movie style):")
        object = st.text_area("Describe the character you want to create (e.g., a boy in school uniform):")
        ratio = st.radio("Select image ratio:", ("16:9", "1:1"))

        # 데이터 제출
        if st.button("Create Character"):
            if style and object:
                st.session_state.review_submitted = False
                st.session_state.image_url = None
                st.session_state.original_ratio = ratio  # 비율 저장
                survey_data = {"style": style, "object": object}
                is_inappropriate, message = filter_inappropriate_content_gpt(f"{style} {object}")
                if is_inappropriate:
                    # 부적절한 내용이 감지된 경우 에러 메시지 출력
                    st.error(message)
                else:
                    st.write("Submitted!")
                    with st.spinner("Creating your character... This may take 40-60 seconds..."):
                        gpt_response = send_to_gpt(survey_data)
                        task_id = create_img(gpt_response, ratio)
                        if task_id:
                            st.session_state.task_id = task_id
                            st.session_state.image_url = check_task_status(task_id)
                            data = {
                                "style": style,
                                "object": object,
                                "ratio": ratio,
                                "gpt_prompt": gpt_response,
                                "img_url": st.session_state.image_url
                            }

                            response = supabase.table("image_user").insert(data).execute()
                            print("response", response.data[0]["id"])
                            if response.data:
                                st.session_state.row_id = response.data[0]["id"]
                                st.rerun()

    # 이미지 출력 및 버튼 표시
    # if st.session_state.image_url:
    #     st.image(st.session_state.image_url, caption="Image from URL", use_container_width=True)
    #     # st.title("제일 만족스러운 이미지를 골라주세요! ")
    # 이미지 출력 및 초기 업스케일 버튼 표시
    if st.session_state.image_url and not st.session_state.upscaled_image_url and not st.session_state.character_created:
        st.image(st.session_state.image_url, caption="Generated Character", use_container_width=True)
        
        # 업스케일링 UI - 캐릭터 초기 생성 후
        st.write("Select an image to upscale:")
        cols = st.columns(2)
        with cols[0]:
            if st.button("Top Left", key="char_up_1"):
                st.session_state.selected_index = 1
        with cols[1]:
            if st.button("Top Right", key="char_up_2"):
                st.session_state.selected_index = 2
        cols = st.columns(2)
        with cols[0]:
            if st.button("Bottom Left", key="char_up_3"):
                st.session_state.selected_index = 3
        with cols[1]:
            if st.button("Bottom Right", key="char_up_4"):
                st.session_state.selected_index = 4
                
    # 캐릭터 업스케일링 작업 수행
    if st.session_state.selected_index is not None and not st.session_state.upscaled_image_url and not st.session_state.character_created:
        with st.spinner("Upscaling character image..."):
            task_id_upscale = upscale(st.session_state.task_id, st.session_state.selected_index)
            st.session_state.upscaled_image_url = check_task_status(task_id_upscale)
            if st.session_state.upscaled_image_url:
                updates = {"upscaled_img_url": st.session_state.upscaled_image_url}
                supabase.table("image_user").update(updates).eq("id", st.session_state.row_id).execute()
                st.session_state.character_created = True
                st.rerun()
                
    # 캐릭터 생성 및 업스케일 완료 후, 동작 생성 단계
    if st.session_state.character_created and st.session_state.upscaled_image_url:
        st.image(st.session_state.upscaled_image_url, caption="Upscaled Character", use_container_width=True)
        
        # 캐릭터 동작 입력 UI
        st.subheader("Create Different Poses with Same Character")
        action_prompt = st.text_area("Describe the pose or action for your character:", 
                                    placeholder="Examples: reading a book, smiling, dancing ... ")
        
        if st.button("Create Action Image"):
            if action_prompt:
                with st.spinner("Creating action image... Please wait..."):
                    # 캐릭터 일관성 유지를 위한 API 호출
                    action_task_id = create_action_img(action_prompt, st.session_state.upscaled_image_url, st.session_state.original_ratio)
                    if action_task_id:
                        st.session_state.action_task_id = action_task_id
                        st.session_state.action_image_url = check_task_status(action_task_id)
                        
                        # 데이터베이스에 동작 이미지 정보 저장
                        action_data = {
                            "parent_id": st.session_state.row_id,
                            "action_prompt": action_prompt,
                            "action_img_url": st.session_state.action_image_url
                        }
                        action_response = supabase.table("image_actions").insert(action_data).execute()
                        if action_response.data:
                            st.session_state.action_id = action_response.data[0]["id"]
                            st.rerun()
                            
        # 비디오 생성 버튼
        if st.button("Create a Video", key="create_video_btn"):
            st.session_state.video_creating = True
            
        # 비디오 생성 UI
        if st.session_state.video_creating:
            st.subheader("Create a video with your character")
            video_prompt = st.text_area(
                "Describe how your character should move in the video:", 
                key="video_prompt_input",
                placeholder="Example: character turning around, character walking, character moving hair in the wind"
            )
            
            if st.button("Generate Video", key="generate_video_btn"):
                if video_prompt:
                    with st.spinner("Creating video... This may take a minute or two..."):
                        try:
                            # Initialize Vidu client
                            vidu = ViduAI(VIDU_API_KEY)
                            
                            # Make the API call
                            response = vidu.image_to_video(
                                images=[st.session_state.upscaled_image_url],
                                prompt=video_prompt,
                                duration=4,
                                resolution="720p",
                                wait_for_completion=True
                            )
                            
                            # If successful, store the video URL
                            if response.get("state") == "success":
                                creations = response.get("creations", [])
                                if creations and len(creations) > 0:
                                    st.session_state.video_url = creations[0].get("url")
                                    st.session_state.video_prompt = video_prompt
                                    
                                    # 데이터베이스에 비디오 정보 저장
                                    video_data = {
                                        "parent_id": st.session_state.row_id,
                                        "video_type": "character",
                                        "video_prompt": video_prompt,
                                        "video_url": st.session_state.video_url
                                    }
                                    video_response = supabase.table("image_videos").insert(video_data).execute()
                                    if video_response.data:
                                        st.session_state.video_id = video_response.data[0]["id"]
                            
                                    st.success("Video created successfully!")
                                else:
                                    st.error("No video was created")
                            else:
                                st.error(f"Video creation failed: {response.get('state')}")
                                
                        except Exception as e:
                            st.error(f"Error creating video: {e}")
            
            # Display the video if available
            if st.session_state.video_url:
                st.subheader("Your character animation")
                st.video(st.session_state.video_url)
                st.caption(f"Video prompt: {st.session_state.video_prompt}")
                
        

    # 동작 이미지 생성 완료 후 표시 및 설문 진행
    if st.session_state.action_image_url and not st.session_state.review_submitted:
        st.image(st.session_state.action_image_url, caption="Generated Action Image", use_container_width=True)
        
        # 새 설문조사 UI
        st.markdown("<h3 style='font-size:20px;'>Please complete our survey to upscale your image! (All fields are optional)</h3>", unsafe_allow_html=True)
        
        # 만족도 관련 질문
        overall_satisfaction = st.slider("How satisfied are you with this service overall? (1-5)", 1, 5, 5, key="overall_satisfaction")
        
        favorite_feature = st.selectbox(
            "Which feature did you like the most?", 
            ["Character Creation", "Action Image Creation", "Video Creation", "Other"], 
            key="favorite_feature"
        )
        
        character_quality = st.slider("How satisfied are you with the character creation quality? (1-5)", 1, 5, 5, key="character_quality")
        action_quality = st.slider("How satisfied are you with the action image creation quality? (1-5)", 1, 5, 5, key="action_quality")
        video_quality = st.slider("How satisfied are you with the video creation quality? (1-5)", 1, 5, 5, key="video_quality")
        
        # 사용성 관련 질문
        difficulties = st.text_area("Did you encounter any difficulties while using the service?", key="difficulties")
        
        image_speed = st.radio(
            "How did you feel about the image generation speed?", 
            ["Very Fast", "Adequate", "Slow", "Very Slow"], 
            key="image_speed"
        )
        
        video_speed = st.radio(
            "How did you feel about the video generation speed?", 
            ["Very Fast", "Adequate", "Slow", "Very Slow"], 
            key="video_speed"
        )
        
        interface_ease = st.slider("How easy was the interface to use? (1-5)", 1, 5, 5, key="interface_ease")
        
        # 비즈니스 모델 관련 질문
        would_use = st.radio("Would you use this service if it's officially launched?", ["Yes", "No"], key="would_use")
        
        st.subheader("How much would you be willing to pay for this service?")
        one_time_fee = st.selectbox(
            "One-time use:", 
            ["Free", "$1-5", "$5-10", "$10-20", "$20-50", "More than $50"], 
            key="one_time_fee"
        )
        
        subscription_fee = st.selectbox(
            "Monthly subscription:", 
            ["Free", "$1-5", "$5-10", "$10-20", "$20-50", "More than $50"], 
            key="subscription_fee"
        )
        
        # 추가 기능 요청
        st.subheader("Which features would you like to see added?")
        more_action_templates = st.checkbox("More action templates", key="more_action_templates")
        longer_videos = st.checkbox("Longer video generation", key="longer_videos")
        music_effects = st.checkbox("Music/sound effects for videos", key="music_effects")
        gallery_feature = st.checkbox("Character storage and gallery feature", key="gallery_feature")
        social_sharing = st.checkbox("Social media sharing", key="social_sharing")
        other_features = st.text_area("Other features you'd like to see:", key="other_features")
        
        # 개선점 및 기타 의견
        improvements = st.text_area("What aspects of the service need improvement?", key="improvements")
        
        # 연락처 및 추가 질문
        email = st.text_input("Email (optional, to receive updates about beta tests):", key="email")
        problem_solving = st.text_area("What problems do you think this service could solve or make easier?", key="problem_solving")
        
        if st.button("Submit Survey", key="submit_survey"):
            # 설문조사 데이터 준비
            review_data = {
                "overall_satisfaction": overall_satisfaction,
                "favorite_feature": favorite_feature,
                "character_quality": character_quality,
                "action_quality": action_quality,
                "video_quality": video_quality,
                "difficulties": difficulties,
                "image_speed": image_speed,
                "video_speed": video_speed,
                "interface_ease": interface_ease,
                "would_use": would_use == "Yes",
                "one_time_fee": one_time_fee,
                "subscription_fee": subscription_fee,
                "more_action_templates": more_action_templates,
                "longer_videos": longer_videos,
                "music_effects": music_effects,
                "gallery_feature": gallery_feature,
                "social_sharing": social_sharing,
                "other_features": other_features,
                "improvements": improvements,
                "email": email or None,
                "problem_solving": problem_solving
            }
            
            # 데이터베이스에 설문조사 결과 저장
            try:
                response = supabase.table("image_user").update(review_data).eq("id", st.session_state.row_id).execute()
                if response.data:
                    st.session_state.review_submitted = True
                    st.success("Thank you for your feedback! It will help us improve our service.")
                    st.rerun()
                else:
                    st.error("Failed to submit survey. Please try again.")
            except Exception as e:
                st.error(f"Error submitting survey: {e}")

    # 리뷰 제출 후 동작 이미지 업스케일 가능
    if st.session_state.review_submitted and st.session_state.action_image_url and not st.session_state.action_upscaled_image_url:
        # 이미지는 위에서 이미 표시되었으므로 여기서는 표시하지 않음
        st.image(st.session_state.action_image_url, caption="Generated Action Image", use_container_width=True)  # 🔧 이 줄 추가
        st.write("Select an action image to upscale:")
        cols = st.columns(2)
        with cols[0]:
            if st.button("Top Left", key="action_up_1"):
                st.session_state.action_selected_index = 1
        with cols[1]:
            if st.button("Top Right", key="action_up_2"):
                st.session_state.action_selected_index = 2
        cols = st.columns(2)
        with cols[0]:
            if st.button("Bottom Left", key="action_up_3"):
                st.session_state.action_selected_index = 3
        with cols[1]:
            if st.button("Bottom Right", key="action_up_4"):
                st.session_state.action_selected_index = 4

    # 동작 이미지 업스케일링 작업 수행
    if st.session_state.action_selected_index is not None and not st.session_state.action_upscaled_image_url:
        with st.spinner("Upscaling action image..."):
            action_upscale_task_id = upscale(st.session_state.action_task_id, st.session_state.action_selected_index)
            st.session_state.action_upscaled_image_url = check_task_status(action_upscale_task_id)
            
            if st.session_state.action_upscaled_image_url:
                updates = {"action_upscaled_img_url": st.session_state.action_upscaled_image_url}
                supabase.table("image_actions").update(updates).eq("id", st.session_state.action_id).execute()
                st.rerun()
                
    # 최종 업스케일된 동작 이미지 표시
    if st.session_state.action_upscaled_image_url:
        st.image(st.session_state.action_upscaled_image_url, caption="Upscaled Action Image", use_container_width=True)
        
        # 동작 이미지로 비디오 생성 버튼
        if st.button("Create a Video from Action Image", key="create_action_video_btn"):
            st.session_state.action_video_creating = True
        
        # 동작 이미지로 비디오 생성 UI
        if "action_video_creating" in st.session_state and st.session_state.action_video_creating:
            st.subheader("Create a video with your character's action")
            action_video_prompt = st.text_area(
                "Describe how your character should move in the video:", 
                key="action_video_prompt_input",
                placeholder="Example: character turning around, character walking, character moving hair in the wind"
            )
            
            if st.button("Generate Action Video", key="generate_action_video_btn"):
                if action_video_prompt:
                    with st.spinner("Creating video... This may take a minute or two..."):
                        try:
                            # Initialize Vidu client
                            vidu = ViduAI(VIDU_API_KEY)
                            
                            # Make the API call with action image
                            response = vidu.image_to_video(
                                images=[st.session_state.action_upscaled_image_url],
                                prompt=action_video_prompt,
                                duration=4,
                                resolution="720p",
                                wait_for_completion=True
                            )
                            
                            # If successful, store the video URL
                            if response.get("state") == "success":
                                creations = response.get("creations", [])
                                if creations and len(creations) > 0:
                                    st.session_state.action_video_url = creations[0].get("url")
                                    st.session_state.action_video_prompt = action_video_prompt
                                    
                                    try:
                                        # 먼저 action_id로 시도
                                        action_video_data = {
                                            "parent_id": st.session_state.action_id,
                                            "video_type": "action",
                                            "video_prompt": action_video_prompt,
                                            "video_url": st.session_state.action_video_url
                                        }
                                        action_video_response = supabase.table("image_videos").insert(action_video_data).execute()
                                        if action_video_response.data:
                                            st.session_state.action_video_id = action_video_response.data[0]["id"]
                                    except Exception as e:
                                        # 실패하면 row_id(image_user의 ID)로 시도
                                        try:
                                            action_video_data = {
                                                "parent_id": st.session_state.row_id,
                                                "video_type": "action",
                                                "video_prompt": action_video_prompt,
                                                "video_url": st.session_state.action_video_url
                                            }
                                            action_video_response = supabase.table("image_videos").insert(action_video_data).execute()
                                            if action_video_response.data:
                                                st.session_state.action_video_id = action_video_response.data[0]["id"]
                                        except Exception as e2:
                                            st.error(f"Error saving video data: {e2}")
                                    
                                    st.success("Action video created successfully!")
                                else:
                                    st.error("No video was created")
                            else:
                                st.error(f"Video creation failed: {response.get('state')}")
                                
                        except Exception as e:
                            st.error(f"Error creating video: {e}")
            
            # Display the action video if available
            if "action_video_url" in st.session_state and st.session_state.action_video_url:
                st.subheader("Your character action animation")
                st.video(st.session_state.action_video_url)
                st.caption(f"Video prompt: {st.session_state.action_video_prompt}")
        
        # 추가 동작 생성 옵션
        if st.button("Create Another Action"):
            # 동작 관련 상태 초기화하고 캐릭터는 유지
            st.session_state.action_image_url = None
            st.session_state.action_task_id = None
            st.session_state.action_selected_index = None
            st.session_state.action_upscaled_image_url = None
            st.session_state.review_submitted = False
            st.rerun()


if __name__ == "__main__":
    main()