FROM node:22-alpine AS build

WORKDIR /app

COPY package.json .
RUN npm install

COPY src ./src
COPY index.html .

RUN npm run build

FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
