FROM node:lts-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the code
COPY . .

EXPOSE 5173

# Run Vite with --host to allow external access from Docker
CMD ["npm", "run", "dev", "--", "--host"]