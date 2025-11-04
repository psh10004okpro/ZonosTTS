# Frontend Dockerfile

FROM node:18-alpine

# 작업 디렉토리 설정
WORKDIR /app

# package.json 및 package-lock.json 복사
COPY package*.json ./

# 의존성 설치
RUN npm install

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 3000

# 개발 서버 실행
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

# 프로덕션 빌드를 위한 대안:
# RUN npm run build
# RUN npm install -g serve
# CMD ["serve", "-s", "dist", "-l", "3000"]
