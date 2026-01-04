# 1. Use an official Python image as the base
FROM python:3.11-slim

# 2. Set the directory inside the container where your code will live
WORKDIR /app

# 3. Copy the requirements file first (this makes builds faster)
COPY requirements.txt .

# 4. Install the Python libraries needed for your app
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of your backend code into the container
COPY . .

# 6. The command to start your API when the container launches
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]