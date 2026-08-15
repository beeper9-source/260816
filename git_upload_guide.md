# 🚀 HMM 클래식 기타 운지 자동 표기 웹 서비스 - 깃허브 업로드 및 배포 가이드

이 프로젝트는 서버리스(Serverless) 웹 애플리케이션으로, **GitHub Pages**를 활용하여 전 세계 어디서든 웹 상에서 무료로 무료 접속하고 실행할 수 있습니다. 

아래 순서대로 따라 하시면 5분 안에 웹 링크로 배포가 완료됩니다!

---

## 📁 배포에 필요한 파일 목록
프로젝트 폴더 내 다음 파일들이 모두 한 디렉토리에 있어야 합니다:
1. `index.html` (웹 UI)
2. `styles.css` (디자인/CSS)
3. `app.js` (UI 연동)
4. `pyodide_worker.js` (백그라운드 Python 실행 엔진)
5. `guitar_hmm.py` (HMM 수학 모델)
6. `mxl_parser.py` (MusicXML 파서)

---

## 💻 1단계: 로컬에서 웹 서비스 확인해 보기 (선택 사항)
먼저 브라우저에서 잘 작동하는지 깃허브에 올리기 전에 내 컴퓨터에서 테스트해 봅니다.
프로젝트 폴더 내에서 터미널(PowerShell 또는 Command Prompt)을 열고 아래 명령어를 입력합니다:

```powershell
python -m http.server 8000
```
그 후 크롬 등 웹 브라우저를 열고 `http://localhost:8000` 에 접속하여 정상적으로 작동(로딩 완료 후 드래그 앤 드롭 업로드 대기 화면으로 진입)하는지 확인합니다.

---

## 🌐 2단계: GitHub에 코드 올리기

### 1. GitHub 로그인 및 새 저장소(Repository) 만들기
1. [GitHub](https://github.com/)에 로그인합니다.
2. 우측 상단 `+` 버튼 클릭 후 **"New repository"**를 선택합니다.
3. **Repository name**에 원하는 이름(예: `guitar-fingering-annotator`)을 입력합니다.
4. **Public**(공개)으로 설정해야 GitHub Pages(무료 웹호스팅)를 쓸 수 있으므로, 반드시 **Public**을 선택해 주세요.
5. "Initialize this repository with..." 체크박스는 모두 **해제**한 채 하단의 **"Create repository"** 버튼을 누릅니다.

### 2. Git 명령어로 코드 올리기
로컬 프로젝트 폴더(`c:\PJT\260816`)에서 터미널을 열고 다음 명령어들을 순서대로 입력합니다:

```powershell
# 1. git 초기화
git init

# 2. 업로드할 파일 전체 추가
git add index.html styles.css app.js pyodide_worker.js guitar_hmm.py mxl_parser.py

# 3. 첫 번째 커밋 기록 작성
git commit -m "Initial release of web-based guitar fingering annotator"

# 4. 기본 브랜치 이름을 main으로 변경
git branch -M main

# 5. 내 GitHub 원격 저장소 연결 (username과 repository-name에 본인 정보를 기입하세요)
git remote add origin https://github.com/본인의깃허브아이디/guitar-fingering-annotator.git

# 6. GitHub에 코드 푸시 (로그인 창이 뜨면 로그인 진행)
git push -u origin main
```

---

## ⚙️ 3단계: GitHub Pages 활성화하기 (웹에 배포)

코드가 깃허브에 잘 업로드되었다면, 깃허브 웹 화면에서 몇 가지 설정만으로 배포할 수 있습니다.

1. 본인의 GitHub 저장소 페이지 상단의 **Settings** (톱니바퀴 모양 아이콘) 탭을 클릭합니다.
2. 좌측 사이드바에서 **Code and automation** 카테고리 하위의 **Pages** 메뉴를 선택합니다.
3. **Build and deployment** 섹션의 **Source** 드롭다운이 **"Deploy from a branch"**로 되어 있는지 확인합니다.
4. 바로 아래 **Branch** 설정에서 `None`으로 되어 있는 드롭다운을 **`main`** 브랜치로 변경하고, 우측 폴더 경로가 **`/ (root)`**인지 확인한 후 **"Save"** 버튼을 클릭합니다.

---

## 🎉 4단계: 무료 배포된 웹 브라우저 주소 확인

저장 후 약 1~2분 정도 기다리시면, GitHub Pages 페이지 상단에 다음과 같은 형식의 실시간 웹 주소가 생성됩니다:

> **🔗 실시간 웹 서비스 주소:**
> `https://본인의깃허브아이디.github.io/guitar-fingering-annotator/`

이 링크를 통해 어디서든 웹브라우저에서 `.mxl` 파일을 업로드하면 즉시 클래식 기타 운지가 표기된 `.mxl` 파일로 변환하여 다운로드받으실 수 있습니다!
