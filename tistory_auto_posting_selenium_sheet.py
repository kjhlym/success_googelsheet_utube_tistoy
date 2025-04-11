'''
유튜브 영상을 기반으로 티스토리 블로그에 자동으로 콘텐츠를 생성하고 포스팅하는 스크립트
구글 시트에 있는 영상 제목과 채널 제목을 가져와서
Gemini API로 콘텐츠를 생성하고 티스토리에 자동 업로드
'''

from time import sleep
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import platform
import subprocess
import pyperclip
from selenium.webdriver import ActionChains
from selenium.webdriver.common.keys import Keys
import os
import json
from datetime import datetime
from googleapiclient.discovery import build
from dotenv import load_dotenv
import google.generativeai as genai
import markdown2

# 환경 변수 로드
load_dotenv()

# API 키 및 계정 정보
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-1.5-pro-latest')
TISTORY_ID = os.getenv('TISTORY_ID')
TISTORY_PASSWORD = os.getenv('TISTORY_PASSWORD')
KAKAO_ID = os.getenv('KAKAO_ID')
KAKAO_PW = os.getenv('KAKAO_PW')

# Gemini API 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-pro-exp-02-05')

C_END = "\033[0m"
C_BOLD = "\033[1m"
C_INVERSE = "\033[7m"
C_BLACK = "\033[30m"
C_RED = "\033[31m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_BLUE = "\033[34m"
C_PURPLE = "\033[35m"
C_CYAN = "\033[36m"
C_WHITE = "\033[37m"
C_BGBLACK = "\033[40m"
C_BGRED = "\033[41m"
C_BGGREEN = "\033[42m"
C_BGYELLOW = "\033[43m"
C_BGBLUE = "\033[44m"
C_BGPURPLE = "\033[45m"
C_BGCYAN = "\033[46m"
C_BGWHITE = "\033[47m"

osName = platform.system()  # window 인지 mac 인지 알아내기 위한

# 대기 시간 최적화 (기존 값 감소)
LOADING_WAIT_TIME = 3  # 5초에서 3초로 감소
PAUSE_TIME = 1  # 3초에서 1초로 감소

tistory_blog_name = 'https://yourblog.tistory.com'  # 자신의 티스토리 블로그 주소로 변경하세요
tistory_category_name = 'IT'  # 원하는 카테고리로 변경하세요

def init_driver():
    try:
        # Chrome 설정
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        # 성능 개선을 위한 추가 옵션
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-notifications")
        
        # ChromeProfile 디렉토리 설정 (기존 프로필 사용)
        user_data_dir = os.path.join(os.getcwd(), "ChromeProfile")
        options.add_argument(f"--user-data-dir={user_data_dir}")
        
        # 새 창으로 시작하기 위한 설정
        options.add_argument("--new-window")
        
        # ChromeDriver 초기화
        service = ChromeService()
        driver = webdriver.Chrome(service=service, options=options)
        
        driver.implicitly_wait(LOADING_WAIT_TIME)
        print("Chrome WebDriver 초기화 성공")
        return driver
        
    except Exception as e:
        print(f"브라우저 초기화 실패: {str(e)}")
        return None


def tistory_login(_driver):
    try:
        # 이미 로그인되어 있는지 확인 (프로필 아이콘 찾기)
        try:
            profile = _driver.find_element(By.CLASS_NAME, 'link_profile')
            print('이미 로그인 되어있습니다.')
            return
        except:
            # 로그인이 필요한 경우에만 아래 코드 실행
            pass
            
        _driver.get('https://www.tistory.com/auth/login')
        _driver.implicitly_wait(LOADING_WAIT_TIME)
        _driver.find_element(By.CLASS_NAME, 'link_kakao_id').click()
        _driver.implicitly_wait(LOADING_WAIT_TIME)
     
        
        if not KAKAO_ID or not KAKAO_PW:
            raise Exception("카카오 로그인 정보가 .env 파일에 설정되지 않았습니다.")
            
        # 카카오 아이디 입력
        id_field = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='loginId']"))
        )
        id_field.click()
        id_field.send_keys(KAKAO_ID)
        
        # 카카오 비밀번호 입력
        pw_field = WebDriverWait(_driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
        )
        pw_field.click()
        pw_field.send_keys(KAKAO_PW)
        
        # 로그인 버튼 클릭
        login_button = WebDriverWait(_driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        login_button.click()
    
        print(f'\n{C_BOLD}{C_RED}{C_BGBLACK}주의: 로그인 진행 중... 60초 동안 대기합니다.{C_END}')
        # 대기 시간 3분에서 1분으로 단축
        WebDriverWait(_driver, 60).until(
            EC.presence_of_element_located(
                (By.CLASS_NAME, 'link_profile')
            )
        )
        print("로그인 완료!")
    except Exception as e:
        print(f'로그인 과정에서 오류 발생: {str(e)}')
    

def search_youtube(query):
    # URL이 직접 입력된 경우 처리
    if 'youtube.com/watch?v=' in query or 'youtu.be/' in query:
        try:
            # URL에서 video_id 추출
            if 'youtube.com/watch?v=' in query:
                video_id = query.split('watch?v=')[1].split('&')[0]
            elif 'youtu.be/' in query:
                video_id = query.split('youtu.be/')[1].split('?')[0]
            
            print(f"YouTube URL이 감지되었습니다. Video ID: {video_id}")
            
            # API 키 유효성 확인
            if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == '':
                print("YouTube API 키가 설정되지 않았습니다. 기본 정보만으로 진행합니다.")
                # API 키 없이 기본 데이터 생성
                data = {
                    'video_id': video_id,
                    'title': f"YouTube 영상 ({video_id})",
                    'description': "YouTube 영상에 대한 설명입니다.",
                    'channel_title': "YouTube 채널",
                    'upload_date': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                    'view_count': "0",
                    'tags': [],
                    'search_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # YouTube 페이지 직접 스크래핑 제안 메시지
                print("참고: API 키가 없어 상세 정보를 가져올 수 없습니다.")
            else:
                # API 키가 있는 경우 정보 가져오기 시도
                try:
                    youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
                    video_response = youtube.videos().list(
                        part='snippet,statistics',
                        id=video_id
                    ).execute()
                    
                    if not video_response['items']:
                        raise Exception("비디오 정보를 찾을 수 없습니다.")
                        
                    video_info = video_response['items'][0]
                    data = {
                        'video_id': video_id,
                        'title': video_info['snippet']['title'],
                        'description': video_info['snippet']['description'],
                        'channel_title': video_info['snippet']['channelTitle'],
                        'upload_date': video_info['snippet']['publishedAt'],
                        'view_count': video_info['statistics']['viewCount'],
                        'tags': video_info['snippet'].get('tags', []),
                        'search_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                except Exception as api_err:
                    print(f"YouTube API 호출 실패: {str(api_err)}")
                    # API 호출 실패 시 기본 데이터 사용
                    data = {
                        'video_id': video_id,
                        'title': f"YouTube 영상 ({video_id})",
                        'description': "YouTube API 호출 실패로 상세 정보를 가져올 수 없습니다.",
                        'channel_title': "YouTube 채널",
                        'upload_date': datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'),
                        'view_count': "0",
                        'tags': [],
                        'search_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
            
            # JSON 파일 저장
            os.makedirs('json', exist_ok=True)
            filename = f"json/youtube_video_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
            return filename
            
        except Exception as e:
            print(f"YouTube URL 처리 중 오류 발생: {str(e)}")
            return None
    
    # 일반 검색어인 경우 기존 API 검색 로직 실행
    try:
        # API 키 확인
        if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == '':
            print("YouTube API 키가 설정되지 않았습니다. API 검색을 진행할 수 없습니다.")
            return None
            
        # API를 통한 검색
        youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)
        search_response = youtube.search().list(
            q=query,
            part='id,snippet',
            maxResults=5,
            type='video'
        ).execute()
        
        if not search_response['items']:
            print("검색 결과가 없습니다.")
            return None
            
        # 첫 번째 결과 선택
        video_id = search_response['items'][0]['id']['videoId']
        
        # 비디오 상세 정보 가져오기
        video_response = youtube.videos().list(
            part='snippet,statistics',
            id=video_id
        ).execute()
        
        if not video_response['items']:
            print("비디오 정보를 찾을 수 없습니다.")
            return None
            
        video_info = video_response['items'][0]
        
        # 데이터 구성
        data = {
            'video_id': video_id,
            'title': video_info['snippet']['title'],
            'description': video_info['snippet']['description'],
            'channel_title': video_info['snippet']['channelTitle'],
            'upload_date': video_info['snippet']['publishedAt'],
            'view_count': video_info['statistics']['viewCount'],
            'tags': video_info['snippet'].get('tags', []),
            'search_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # JSON 파일 저장
        os.makedirs('json', exist_ok=True)
        filename = f"json/youtube_video_{video_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        return filename
    
    except Exception as e:
        print(f"YouTube 검색 중 오류 발생: {str(e)}")
        return None


def generate_content_with_gemini(video_data):
    """Gemini API를 사용하여 블로그 콘텐츠 생성"""
    
    if not GEMINI_API_KEY:
        print("Gemini API 키가 설정되지 않았습니다.")
        return None
        
    try:
        # 영상 정보 추출
        title = video_data.get('title', '')
        description = video_data.get('description', '')
        channel = video_data.get('channel_title', '')
        tags = video_data.get('tags', [])
        
        # 태그 문자열 생성
        tags_str = ', '.join(tags[:10]) if tags else ""
        
        # 프롬프트 구성 - 블로그 작성용
        prompt = f"""
        유튜브 영상 정보를 기반으로 티스토리 블로그 포스팅용 콘텐츠를 작성해주세요.
        
        # 영상 정보
        - 제목: {title}
        - 채널: {channel}
        - 태그: {tags_str}
        - 설명: {description[:500]}...
        
        # 요구사항
        1. 한국어로 작성해주세요.
        2. 블로그 제목은 SEO에 최적화되게 영상 제목을 수정해주세요.
        3. 서론, 본론, 결론 구조로 작성해주세요.
        4. 본론은 주요 내용을 3-5개의 소제목으로 나누어 작성해주세요.
        5. 마크다운 형식으로 작성해주세요.
        6. 소제목은 ## 헤더로 작성해주세요.
        7. 글자 수는 2000자 이상으로 작성해주세요.
        8. 적절한 곳에 이미지 삽입 및 표를 활용하면 좋습니다.
        9. 전문적이고 교육적인 내용으로 작성해주세요.
        10. 블로그 글의 첫 부분에 원본 영상 링크를 포함해주세요: https://youtu.be/{video_data.get('video_id', '')}
        
        # 최종 출력 형식
        ```
        # [블로그 제목]
        
        원본 영상: https://youtu.be/{video_data.get('video_id', '')}
        
        [서론]
        
        ## [소제목 1]
        [내용]
        
        ## [소제목 2]
        [내용]
        
        ## [소제목 3]
        [내용]
        
        [결론]
        ```
        """
        
        # 프롬프트가 너무 길면 잘라내기
        if len(prompt) > 15000:
            prompt = prompt[:15000]
            
        # Gemini API 호출
        result = model.generate_content(
            contents=[prompt]
        )
        
        # 결과 텍스트 반환
        return result.text
        
    except Exception as e:
        print(f"Gemini API 호출 중 오류 발생: {str(e)}")
        return None


def create_html_content(json_file):
    """JSON 파일에서 데이터를 로드하고 HTML 콘텐츠 생성"""
    
    try:
        # JSON 파일 로드
        with open(json_file, 'r', encoding='utf-8') as f:
            video_data = json.load(f)
            
        # Gemini로 콘텐츠 생성
        markdown_content = generate_content_with_gemini(video_data)
        
        if not markdown_content:
            print("콘텐츠 생성에 실패했습니다.")
            return None, None
            
        # 마크다운을 HTML로 변환
        html_content = markdown2.markdown(markdown_content)
        
        # 첫 번째 줄을 제목으로 추출
        lines = markdown_content.strip().split('\n')
        title = ""
        
        for line in lines:
            if line.startswith('# '):
                title = line.replace('# ', '')
                break
                
        if not title:
            title = f"{video_data['title']} - 리뷰 및 분석"
            
        return title, html_content
            
    except Exception as e:
        print(f"HTML 콘텐츠 생성 중 오류 발생: {str(e)}")
        return None, None


def tistory_write(_driver, json_file):
    """티스토리에 글 작성"""
    
    try:
        # 타이틀과 HTML 콘텐츠 생성
        title, html_content = create_html_content(json_file)
        
        if not title or not html_content:
            print("콘텐츠를 생성할 수 없습니다.")
            return False
            
        # 티스토리 글 작성 페이지로 이동
        _driver.get(f"{tistory_blog_name}/manage/write/")
        
        # 대기 시간
        WebDriverWait(_driver, LOADING_WAIT_TIME*2).until(
            EC.presence_of_element_located((By.ID, "editor"))
        )
        
        # 제목 입력
        title_input = _driver.find_element(By.CLASS_NAME, "textarea_tit")
        title_input.clear()
        title_input.send_keys(title)
        
        # HTML 모드로 전환
        _driver.find_element(By.CLASS_NAME, "btn_html").click()
        sleep(PAUSE_TIME)
        
        # HTML 입력 필드
        html_frame = _driver.find_element(By.CLASS_NAME, "CodeMirror-scroll")
        html_frame.click()
        
        # 클립보드를 통해 HTML 내용 붙여넣기
        pyperclip.copy(html_content)
        
        # 운영 체제에 맞는 붙여넣기 단축키 사용
        actions = ActionChains(_driver)
        if osName == "Darwin":  # Mac OS
            actions.key_down(Keys.COMMAND).send_keys('v').key_up(Keys.COMMAND)
        else:  # Windows
            actions.key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL)
        actions.perform()
        
        sleep(PAUSE_TIME)
        
        # 카테고리 선택
        try:
            # 카테고리 드롭다운 메뉴 클릭
            category_element = WebDriverWait(_driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "btn_category"))
            )
            category_element.click()
            
            # 카테고리 목록에서 원하는 카테고리 찾기
            category_list = WebDriverWait(_driver, 5).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".list_category li"))
            )
            
            target_category = None
            for category in category_list:
                if tistory_category_name in category.text:
                    target_category = category
                    break
                    
            if target_category:
                target_category.click()
                print(f"카테고리 '{tistory_category_name}'로 설정됨")
            else:
                print(f"카테고리 '{tistory_category_name}'를 찾을 수 없음. 기본 카테고리 사용")
        except Exception as e:
            print(f"카테고리 설정 중 오류: {str(e)}")
            
        # 태그 설정
        try:
            # JSON 파일 로드
            with open(json_file, 'r', encoding='utf-8') as f:
                video_data = json.load(f)
                
            # 태그가 있는 경우에만 처리
            tags = video_data.get('tags', [])
            if tags:
                # 태그 입력 필드
                tag_input = _driver.find_element(By.CLASS_NAME, "wrap_tag")
                tag_input.click()
                
                # 태그 입력 (최대 5개)
                for tag in tags[:5]:
                    if tag.strip():
                        actions = ActionChains(_driver)
                        actions.send_keys(tag)
                        actions.send_keys(Keys.ENTER)
                        actions.perform()
                        sleep(0.3)  # 태그 입력 사이에 잠시 대기
        except Exception as e:
            print(f"태그 설정 중 오류: {str(e)}")
            
        # 콘텐츠 저장
        try:
            _driver.find_element(By.CLASS_NAME, "btn_save").click()
            
            # 저장 확인 대화상자 처리
            WebDriverWait(_driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".btn_g.btn_confirm"))
            ).click()
            
            # 저장 완료 상태 확인 (성공 메시지 대기)
            WebDriverWait(_driver, 30).until(
                EC.visibility_of_element_located((By.CLASS_NAME, "layer_complete"))
            )
            
            print(f"\n{C_BOLD}{C_GREEN}게시물이 성공적으로 저장되었습니다!{C_END}")
            return True
                
        except Exception as e:
            print(f"게시물 저장 중 오류: {str(e)}")
            return False
            
    except Exception as e:
        print(f"티스토리 글 작성 중 오류 발생: {str(e)}")
        return False


def main():
    """메인 함수"""
    
    print(f"\n{C_BOLD}{C_BGGREEN}{C_BLACK} YouTube 영상 기반 티스토리 자동 포스팅 도구 {C_END}")
    print(f"{C_BOLD}=== 환경 설정 확인 ==={C_END}")
    
    # 필수 API 키 확인
    if not YOUTUBE_API_KEY:
        print(f"{C_RED}경고: YouTube API 키가 설정되지 않았습니다. 영상 URL을 직접 입력해야 합니다.{C_END}")
    
    if not GEMINI_API_KEY:
        print(f"{C_RED}경고: Gemini API 키가 설정되지 않았습니다. 콘텐츠 생성이 불가능합니다.{C_END}")
        return
    
    if not KAKAO_ID or not KAKAO_PW:
        print(f"{C_RED}경고: 카카오 로그인 정보가 설정되지 않았습니다. 티스토리 로그인이 불가능합니다.{C_END}")
        return
    
    # 웹드라이버 초기화
    driver = init_driver()
    if not driver:
        print(f"{C_RED}오류: 웹드라이버를 초기화할 수 없습니다.{C_END}")
        return
    
    try:
        # 티스토리 로그인
        tistory_login(driver)
        
        while True:
            print(f"\n{C_BOLD}=== 작업 선택 ==={C_END}")
            print("1. YouTube 영상 URL로 포스팅 생성")
            print("2. YouTube 검색어로 포스팅 생성")
            print("3. 종료")
            
            choice = input("\n선택: ")
            
            if choice == "1":
                video_url = input("YouTube 영상 URL을 입력하세요: ")
                json_file = search_youtube(video_url)
                
                if json_file:
                    print(f"\n{C_BOLD}YouTube 정보를 저장했습니다: {json_file}{C_END}")
                    
                    # 티스토리에 포스팅
                    print(f"\n{C_BOLD}티스토리에 포스팅을 시작합니다...{C_END}")
                    success = tistory_write(driver, json_file)
                    
                    if success:
                        print(f"{C_GREEN}포스팅이 완료되었습니다!{C_END}")
                    else:
                        print(f"{C_RED}포스팅 중 오류가 발생했습니다.{C_END}")
                else:
                    print(f"{C_RED}YouTube 정보를 가져오는 데 실패했습니다.{C_END}")
                    
            elif choice == "2":
                search_query = input("YouTube 검색어를 입력하세요: ")
                json_file = search_youtube(search_query)
                
                if json_file:
                    print(f"\n{C_BOLD}YouTube 정보를 저장했습니다: {json_file}{C_END}")
                    
                    # 티스토리에 포스팅
                    print(f"\n{C_BOLD}티스토리에 포스팅을 시작합니다...{C_END}")
                    success = tistory_write(driver, json_file)
                    
                    if success:
                        print(f"{C_GREEN}포스팅이 완료되었습니다!{C_END}")
                    else:
                        print(f"{C_RED}포스팅 중 오류가 발생했습니다.{C_END}")
                else:
                    print(f"{C_RED}YouTube 정보를 가져오는 데 실패했습니다.{C_END}")
                    
            elif choice == "3":
                print(f"{C_BOLD}프로그램을 종료합니다.{C_END}")
                break
                
            else:
                print(f"{C_RED}잘못된 선택입니다. 다시 시도하세요.{C_END}")
                
    except Exception as e:
        print(f"{C_RED}예상치 못한 오류가 발생했습니다: {str(e)}{C_END}")
    finally:
        # 브라우저 종료
        if driver:
            driver.quit()


if __name__ == "__main__":
    main()