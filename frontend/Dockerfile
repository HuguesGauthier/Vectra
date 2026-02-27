# Develop stage
FROM node:20-alpine AS develop-stage
WORKDIR /app
COPY package*.json ./
RUN npm install --ignore-scripts
COPY . .
RUN npm run postinstall

# Build stage
FROM develop-stage AS build-stage
RUN npm run build

# Production stage
FROM nginx:1.25.3-alpine AS production-stage
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build-stage /app/dist/spa /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
