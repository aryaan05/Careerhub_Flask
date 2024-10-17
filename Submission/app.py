from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson import ObjectId


##### Please keep in mind that this entire file makes use of port 5001 as 5000 is occupied for me 

app = Flask(__name__)

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')  
db = client['careerhub'] 

# Define collections which is coherent with the import_data collections 
collections = {
    "jobs": db['jobs'],
    "companies": db['companies'],
    "education_and_skills": db['education_and_skills'],
    "employment_details": db['employment_details'],
    "industry_info": db['industry_info']
}

# as tghis is the homepage it will have yhe basic route of localhost 5001 
@app.route('/')
def welcome():
    # homepage 
    return jsonify(message="Welcome to the homepage!")

def convert_to_dict(document):
    """ Convert a MongoDB document to a regular dictionary, converting ObjectId to string. This is required becauee i have to pull the whole document for a single id
    without this it gives me errors """
    if document:
        doc = document.copy()  # Make a copy of the document
        doc['_id'] = str(doc['_id'])  # Convert ObjectId to string
        return doc
    return None

# this is to search by the job id  and fiollows the get method with paramter job_id in the url 
@app.route('/search_by_job_id/<int:job_id>', methods=['GET'])
def view_job_details(job_id):
    job_details = {}

    # Search in the jobs collection
    job_doc = collections['jobs'].find_one({'id': job_id})
    if job_doc:
        job_details['job'] = convert_to_dict(job_doc)
    else:
        return jsonify({"error": "Job not found"}), 404

    # Search in the companies collection
    company_doc = collections['companies'].find_one({'id': job_id})
    if company_doc:
        job_details['company'] = convert_to_dict(company_doc)

    # Search in the education_and_skills collection
    education_doc = collections['education_and_skills'].find_one({'job_id': job_id})
    if education_doc:
        job_details['education_and_skills'] = convert_to_dict(education_doc)

    # Search in the employment_details collection
    employment_doc = collections['employment_details'].find_one({'id': job_id})
    if employment_doc:
        job_details['employment_details'] = convert_to_dict(employment_doc)

    # Search in the industry_info collection
    industry_doc = collections['industry_info'].find_one({'id': job_id})
    if industry_doc:
        job_details['industry_info'] = convert_to_dict(industry_doc)

    return jsonify(job_details), 200

# Mandatory fields for the creating job post as without these fields it will return an error 
MANDATORY_FIELDS = ['title', 'industry']
# bfunction to create job post. for this you have to put the job post in the body and make sure it has the above mentioned fields 
@app.route('/create/jobPost', methods=['POST'])
def create_job_post():
    data = request.json
    
    # Validation - Check if mandatory fields are present
    missing_fields = [field for field in MANDATORY_FIELDS if field not in data]
    if missing_fields:
        return jsonify({"error": f"Missing mandatory fields: {', '.join(missing_fields)}"}), 400

    # Assign an ID based on the current length of the jobs collection which increments based on the klength of the jobs collection 
    job_id = collections['jobs'].count_documents({}) + 1

    # Create a job post document with ID
    job_post = {'id': job_id}

    # Populate job post with all incoming data
    for field in data:
        job_post[field] = data.get(field, '')

    # Insert the job post into the jobs collection
    collections['jobs'].insert_one(job_post)

    # Check and prepare updates for each collection based on the fields present in the data as other fields are optional 
    for collection_name, collection in collections.items():
        if collection_name != 'jobs':  # Skip the jobs collection
            # Get the schema fields for the collection
            schema_fields = collection.find_one().keys() if collection.count_documents({}) > 0 else []
            
            # Prepare an empty document with job ID
            update_doc = {'id': job_id}

            # Populate fields from incoming data if they exist in the collection schema
            for field in schema_fields:
                if field != '_id':  # Skip the _id field to avoid duplication issues
                    update_doc[field] = data.get(field, '')  # Leave empty if the field is not provided

            # Insert the document into the respective collection
            collections[collection_name].insert_one(update_doc)

    return jsonify({"message": "Job post created successfully", "job_id": job_id}), 201

# updating jobs by job title
@app.route('/update_by_job_title', methods=['GET', 'POST'])
# the get allows us to see how the fields are populated at the moment while the post allows us to make a chnage for the requirewd job title 
# as it has post you will have to include the fields in the body of postman 
def update_job_details():
    if request.method == 'GET':
        title = request.args.get('title')
        job_doc = collections['jobs'].find_one({'title': title})

        if job_doc:
            job_doc['_id'] = str(job_doc['_id'])  # Convert ObjectId to string for JSON serialization
            return jsonify(job_doc), 200
        else:
            return jsonify({"error": "Job not found"}), 404

    elif request.method == 'POST':
        data = request.json
        title = data.get('title')
        
        # Find the job by title
        job_doc = collections['jobs'].find_one({'title': title})

        if job_doc:
            # Prepare updates for the jobs collection
            job_updates = {}
            if 'description' in data:
                job_updates['description'] = data['description']
            if 'average_salary' in data:
                job_updates['average_salary'] = data['average_salary']
            if 'location' in data:
                job_updates['location'] = data['location']

            # Update the job details in the jobs collection
            if job_updates:
                collections['jobs'].update_one({'title': title}, {'$set': job_updates})

            # Prepare updates for other collections based on provided fields
            other_updates = {}
            for collection_name in collections:
                if collection_name != 'jobs':  # Skip the jobs collection
                    for field in data:
                        if field in collections[collection_name].find_one({}).keys():  # Check if field exists in collection
                            other_updates[field] = data[field]

                    if other_updates:  # Only update if there are fields to update
                        # Assuming 'id' is used to relate other collections
                        job_id = job_doc['id']
                        collections[collection_name].update_one({'id': job_id}, {'$set': other_updates}, upsert=True)

            return jsonify({"message": "Job and related details updated successfully"}), 200
        else:
            return jsonify({"error": "Job not found"}), 404

# follows the delete job title and uses the delete method     
@app.route('/delete_by_job_title', methods=['DELETE'])
def delete_job_listing():
    data = request.get_json()

    # Extract title and confirmation from the JSON body
    title = data.get('title')
    confirmation = data.get('confirmation')
    
    # without thge abiove two fields it wil not work - title and confirmation is mandatory 

    if not title:
        return jsonify({"error": "Job title is required"}), 400

    if (confirmation and confirmation.lower() == 'yes') or (confirmation and confirmation.lower() == 'YES')  or (confirmation and confirmation.lower() == 'y') or (confirmation and confirmation.lower() == 'Y'):
        # Find the job by title
        job_doc = collections['jobs'].find_one({'title': title})

        if job_doc:
            # Remove the job from the jobs collection
            collections['jobs'].delete_one({'title': title})

            # Also remove associated entries from other collections
            job_id = job_doc['id']
            for collection_name in collections:
                collections[collection_name].delete_many({'id': job_id})

            return jsonify({"message": "Job and related details deleted successfully"}), 200
        else:
            return jsonify({"error": "Job not found"}), 404
    else:
        return jsonify({"error": "Deletion not confirmed"}), 400


def serialize(data):
    """Convert MongoDB ObjectId to string and prepare data for JSON response."""
    if isinstance(data, list):
        return [serialize(item) for item in data]
    elif isinstance(data, dict):
        return {key: (str(value) if isinstance(value, ObjectId) else value) for key, value in data.items()}
    return data

# this is to get the jobs by salary and it takes in two arguments in the url - min salary and max salary. 
# it is done using this http://localhost:5001/query_jobs_by_salary?min_salary=50000&max_salary=100000 replace the numbers as appropriate 
@app.route('/query_jobs_by_salary', methods=['GET'])
def query_jobs_by_salary():
    min_salary = request.args.get('min_salary', type=float)
    max_salary = request.args.get('max_salary', type=float)

    if min_salary is None or max_salary is None:
        return jsonify({"error": "Both min_salary and max_salary are required"}), 400

    # Find jobs within the specified salary range
    jobs = list(collections['employment_details'].find({
        'average_salary': {
            '$gte': min_salary,
            '$lte': max_salary
        }
    }))
    # this gets rid of the _id made by Mongodb without this it gets error 
    for job in jobs:
        job.pop('_id')
    # print(jobs)
    if not jobs:
        return jsonify({"message": "No jobs found in this salary range"}), 404

    # Prepare a list to hold job details from all collections
    job_details = []

    for job in jobs:
        print(job)
        job_id = job['id']

        # Get related job info
        job_info = collections['jobs'].find_one({'id': job_id})
        company_info = collections['companies'].find_one({'id': job_id})
        education_info = collections['education_and_skills'].find_one({'job_id': job_id})
        industry_info = collections['industry_info'].find_one({'id': job['id']})

        # Combine all information into one dictionary
        combined_info = {
            "job": serialize(job_info),
            "employment_details": serialize(job),
            "company_info": serialize(company_info),
            "education_info": serialize(education_info),
            "industry_info": serialize(industry_info)
        }

        job_details.append(combined_info)

    return jsonify(serialize(job_details)), 200    


# Define experience levels
experience_levels = {
    'Entry Level': (0, 2),    # 0-2 years
    'Mid Level': (3, 6),      # 3-6 years
    'Senior Level': (7, 90)    # 7+ years
}
    
# this is to get the jobs based on the experience level as shown above - if not fromn these 3 it will givce an error 
# http://localhost:5001/jobs?experience_level=Entry%20Level`, where the `experience_level` query parameter can be "Entry Level", "Mid Level", or "Senior Level".  
@app.route('/jobs', methods=['GET'])
def get_jobs_by_experience():
    experience_level = request.args.get('experience_level')
     # checks and throws werror 
    if experience_level not in experience_levels:
        return jsonify({"error": "Invalid experience level provided."}), 400
    
    min_years, max_years = experience_levels[experience_level]

    # Query the jobs collection for the specified experience level
    filtered_jobs = list(collections['jobs'].find({
        "years_of_experience": {"$gte": min_years, "$lte": max_years}
    }))

    # Convert MongoDB documents to JSON-friendly format
    for job in filtered_jobs:
        job['_id'] = str(job['_id'])  # Convert ObjectId to string
    
    return jsonify(filtered_jobs), 200

    




