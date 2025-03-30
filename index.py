import streamlit as st
from google import genai
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Apply custom styles for centering content
st.markdown("""
    <style>
        .block-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)

# UI Layout
st.title("🎓 Course Flow")
st.subheader("Tell us about your academic goals")

# Initialize Gemini API client
api_key = os.getenv("API_KEY")
if not api_key:
    st.error("API Key is missing. Please check your .env file.")
    st.stop()

client = genai.Client(api_key=api_key)

# Dictionary mapping majors to JSON curriculum files
majorDict = {
    "Computer Engineering": "cmpen.json",
    "Aerospace Engineering": "aero.json",
    "Chemical Engineering": "chemeg.json",
    "Civil Engineering": "civeng.json",
    "Computational Data Sciences": "cmpds.json",
    "Computer Science": "cmpsc.json",
    "Electrical Engineering": "EEng.json",
    "Engineering Sciences": "engsci.json",
    "Industrial Engineering": "indeng.json",
    "Nuclear Engineering": "NucEng.json"
}

majorsList = list(majorDict.keys())


def extract_course_codes(json_data):
    """Extracts course codes from a curriculum JSON structure."""
    course_codes = []

    def traverse(obj, in_valid_semester=False):
        if isinstance(obj, dict):
            if "1st Semester" in obj or "2nd Semester" in obj:
                traverse(obj.get("1st Semester", {}), True)
                traverse(obj.get("2nd Semester", {}), True)

            for key, value in obj.items():
                if key == "semester" and value in ["1st Semester", "2nd Semester"]:
                    in_valid_semester = True
                elif key == "courseCode" and in_valid_semester:
                    course_codes.append(value)
                else:
                    traverse(value, in_valid_semester)

        elif isinstance(obj, list):
            for item in obj:
                traverse(item, in_valid_semester)

    traverse(json_data)
    return course_codes


def load_major_data(major):
    """Loads curriculum JSON data based on the selected major."""
    file_path = majorDict.get(major)
    if not file_path or not os.path.exists(file_path):
        st.error(f"Curriculum file for {major} not found.")
        return None
    
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            return data
    except Exception as e:
        st.error(f"Error loading {file_path}: {e}")
        return None


def query_gemini(question, data):
    """Queries the Gemini API with a given curriculum and user question."""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Based on this curriculum:\n{json.dumps(data, indent=2)}\n\n{question}"
        )
        return response.text
    except Exception as e:
        st.error(f"Error querying Gemini API: {e}")
        return None


def filter_courses(data, completed_courses):
    """Filters out the completed courses from the data."""
    filtered_data = {}

    def recursive_filter(obj, completed_courses):
        """Recursively filters out courses by courseCode."""
        if isinstance(obj, dict):
            # Check if it's a valid semester (e.g. "1st Semester", "2nd Semester")
            for key, value in obj.items():
                if key in ["1st Semester", "2nd Semester"]:  # If it's a semester, recurse into it
                    obj[key] = recursive_filter(value, completed_courses)
                elif key == "courseCode" and obj[key] in completed_courses:
                    return None  # Remove the course if it's completed
                else:
                    obj[key] = recursive_filter(value, completed_courses)  # Recurse into nested dictionaries

        elif isinstance(obj, list):
            return [recursive_filter(item, completed_courses) for item in obj]  # Handle lists of courses

        return obj

    # Start filtering the main data structure
    filtered_data = recursive_filter(data, completed_courses)
    return filtered_data


def generate_course_plan(data, major, interests, years_to_graduate, max_credits, completed_courses):
    """Generates a structured course plan using Gemini API."""
    try:
        # Filter out the completed courses from the original data
        filtered_data = filter_courses(data, completed_courses)
        
        # Generate the course plan using the filtered data
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                f"Given the major {major} with interests in {', '.join(interests) if interests else 'none'}, "
                f"and the following curriculum (excluding completed courses):\n{json.dumps(filtered_data, indent=2)}\n"
                f"Please generate a structured course plan in a horizontal table format, "
                "with two semesters per row. The student has already completed the courses marked as completed, "
                "and those courses should not appear in the plan. Ensure completion within eight semesters, "
                "respecting prerequisite constraints and keeping the credit load under 21 per semester. "
                "If it's not possible to create such a plan, indicate that."
            )
        )
        return response.text
    except Exception as e:
        st.error(f"Error generating course plan: {e}")
        return None




def display_checkboxes(items):
    selected_items = []
    
    # Create two columns
    col1, col2 = st.columns(2)
    
    for idx, item in enumerate(items):
        # Ensure unique keys by appending the index
        unique_key = f"checkbox_{item}_{idx}"
        
        # Alternate between columns
        if idx % 2 == 0:
            with col1:
                if st.checkbox(item, key=unique_key):
                    selected_items.append(item)
        else:
            with col2:
                if st.checkbox(item, key=unique_key):
                    selected_items.append(item)
    
    return selected_items



# Create centered columns
col1, col2, col3 = st.columns([1, 25, 1])
with col2:
    major = st.selectbox("Select Your Major", majorsList)
    interest = st.multiselect("Select Interests (for minors/double majors)", [])
    years_to_graduate = st.slider("Years to Graduate", 3, 5, 4)
    max_credits = st.slider("Max Credits Per Semester", 12, 21, 15)

    # Load major-specific data
    data = load_major_data(major)
    if data:
        course_codes = extract_course_codes(data)
        
        st.subheader("📋 Select Completed Courses")
        completed_courses = display_checkboxes(course_codes)
        if st.button("Generate Course Plan"):
            st.subheader("📅 Your Personalized Course Plan")

            # Generate course plan using all selected inputs
            course_plan = generate_course_plan(
                data=data, 
                major=major, 
                interests=interest, 
                years_to_graduate=years_to_graduate, 
                max_credits=max_credits, 
                completed_courses=completed_courses
            )

            if course_plan:
                st.write(course_plan)
            else:
                st.error("Failed to generate a course plan. Please try again.")
