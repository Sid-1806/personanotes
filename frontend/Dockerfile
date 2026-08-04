FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
COPY package*.json ./
RUN npm ci

# Copy remaining source code
COPY . .

# Build the Next.js application
RUN npm run build

# Start the application
CMD ["npm", "start"]
