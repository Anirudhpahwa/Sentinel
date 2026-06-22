FROM node:20-alpine

WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend .

# NEXT_PUBLIC_* vars are inlined into the client bundle at build time, not
# read at container start, so this has to be a build ARG rather than just a
# runtime environment variable in docker-compose.
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build

ENV PORT=3000
EXPOSE 3000

CMD ["npm", "start"]
