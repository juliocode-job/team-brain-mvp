# Step 1: Start with an official Python base image.
# We use a 'slim' version which is smaller and more secure.
FROM python:3.11-slim

# Step 2: Set the working directory inside the container.
# All subsequent commands will run from this directory.
WORKDIR /app

# Step 3: Copy the requirements file into the container.
COPY requirements.txt .

# Step 4: Install the Python dependencies.
# This installs all the libraries from requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the rest of the project files into the container.
# This includes app.py, acls.json, and the 'data' folder.
COPY . .

# Step 6: Expose the port that the Flask app runs on.
# This tells Docker that the container listens on port 5000.
EXPOSE 5000

# Step 7: Define the command to run when the container starts.
# This will run our Flask application server.
CMD ["python", "app.py"]