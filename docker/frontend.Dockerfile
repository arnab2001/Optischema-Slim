FROM node:18-alpine

# Install Python and build tools for native dependencies
RUN apk add --no-cache python3 make g++

# Set working directory
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY frontend/ .

# Expose port
EXPOSE 3000

# Start the application
CMD ["npm", "run", "dev"] 