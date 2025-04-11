# 유튜브 영상 기반 티스토리 자동 포스팅 도구

이 프로젝트는 유튜브 영상 정보를 가져와 Gemini API를 통해 콘텐츠를 생성하고, 이를 티스토리 블로그에 자동으로 포스팅하는 Python 스크립트입니다.

## 주요 기능

- 유튜브 영상 검색 및 메타데이터 추출
- Gemini AI를 활용한 블로그 콘텐츠 자동 생성
- 티스토리 블로그 자동 로그인 및 포스팅
- 크롬 프로필을 통한 로그인 상태 유지

## 설치 방법

1. 저장소 클론:

   ```
   git clone https://github.com/yourusername/success_googelsheet.git
   cd success_googelsheet
   ```

2. 필요한 패키지 설치:

   ```
   pip install -r requirements.txt
   ```

3. 환경 변수 설정 (.env 파일 생성):
   ```
   YOUTUBE_API_KEY=your_youtube_api_key
   GEMINI_API_KEY=your_gemini_api_key
   GEMINI_MODEL=gemini-2.0-pro-exp-02-05
   TISTORY_ID=your_tistory_id
   TISTORY_PASSWORD=your_tistory_password
   ```

## 사용 방법

1. 스크립트 실행:

   ```
   python tistory_auto_posting_selenium_sheet.py
   ```

2. 프롬프트에 따라 유튜브 검색어 또는 유튜브 영상 URL 입력

3. 프로그램이 자동으로:
   - 유튜브 데이터 추출
   - AI로 콘텐츠 생성
   - 티스토리에 포스팅

## 파일 구조

- `tistory_auto_posting_selenium_sheet.py`: 메인 스크립트
- `requirements.txt`: 필요한 패키지 목록
- `.env`: 환경 변수 설정 (생성 필요)
- `json/`: JSON 데이터 저장 디렉토리
- `ChromeProfile/`: 크롬 프로필 데이터 (자동 생성)

## 주의사항

- 첫 실행 시 Chrome 브라우저 로그인 필요 (이후 ChromeProfile에 세션 저장)
- .env 파일에 개인 인증 정보 보관 (GitHub에 업로드하지 않도록 주의)
- API 키 할당량과 사용량 모니터링 필요

## 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.