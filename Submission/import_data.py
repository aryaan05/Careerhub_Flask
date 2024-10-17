import pandas as pd
import json
from pymongo import MongoClient
import os

# Define the CSV files directly in the current directory
csv_files = {
    "jobs": "jobs.csv",
    "companies": "companies.csv",
    "education_and_skills": "education_and_skills.csv",
    "employment_details": "employment_details.csv",
    "industry_info": "industry_info.csv"
}

# Function to transform CSV to JSON
def transform_csv_to_json():
    for key, file_name in csv_files.items():
        df = pd.read_csv(file_name)  # Read directly from the current directory
        json_file_name = f"{key}.json"
        df.to_json(json_file_name, orient='records', lines=True)
        print(f"Transformed {file_name} to {json_file_name}")

# Function to import JSON to MongoDB
def import_json_to_mongodb():
    # Connect to MongoDB
    client = MongoClient('mongodb://localhost:27017/')  
    db = client['careerhub']  
    collections = {
        "jobs": db['jobs'],  
        "companies": db['companies'],  
        "education_and_skills": db['education_and_skills'],  
        "employment_details": db['employment_details'],  
        "industry_info": db['industry_info']  
    }

    for key in collections.keys():
        json_file_name = f"{key}.json"
        try:
            with open(json_file_name, 'r') as f:  # Open each JSON file
                for line in f:
                    try:
                        # Load each line as a JSON object
                        data = json.loads(line.strip())  # Remove any surrounding whitespace
                        # Insert the data into MongoDB
                        collections[key].insert_one(data)
                        print(f"Inserted into {key}: {data}")  # Print the inserted document
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON in {key}: {e}")
                    except Exception as e:
                        print(f"An error occurred while inserting into {key}: {e}")
        except FileNotFoundError:
            print(f"{json_file_name} not found. Skipping...")

    # Close the MongoDB connection
    client.close()

if __name__ == "__main__":
    transform_csv_to_json()  # Transform CSV files to JSON
    import_json_to_mongodb()  # Import the transformed JSON files into MongoDB
