import streamlit as st
from google import genai
import json
import os
from dotenv import load_dotenv
import pandas as pd

# Display the Icon
st.set_page_config(
    page_title="Courseflow",
    page_icon="coursetransicon.png",  
)

hide_decoration_bar_style = '''
    <style>
        header {visibility: hidden;}
    </style>
'''
st.markdown(hide_decoration_bar_style, unsafe_allow_html=True)

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

st.logo("coursetransicon.png")

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

def load_minors():
    """Loads minors from a separate JSON file."""
    try:
        with open("academic_minors.json", "r") as file:
            minors_data = json.load(file)
        return minors_data
    except Exception as e:
        st.error(f"Error loading minors.json: {e}")
        return {}

    
minors_json = load_minors()


minors_list = list(minors_json)



def extract_course_codes(json_data):
    """Extracts course codes from a curriculum JSON structure."""
    course_codes = []

    def traverse(obj, in_valid_semester=False):
        if isinstance(obj, dict):
            if "1st Semester" in obj or "2nd Semester" in obj:
                traverse(obj.get("1st Semester", {}), True)
                traverse(obj.get("2nd Semester", {}), True)
                traverse(obj.get("3rd Semester", {}), True)
                traverse(obj.get("4nd Semester", {}), True)

            for key, value in obj.items():
                if key == "semester" and value in ["1st Semester", "2nd Semester", "3rd Semester", "4th Semester"]:
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


def generate_course_plan(data, major, interests, years_to_graduate, max_credits, completed_courses):
    """Generates a structured course plan using Gemini API and ensures proper JSON output."""

    semesters = years_to_graduate * 2

    try:
        # Define the structured prompt
        prompt = (
            f"Given the major curriculum:\n{json.dumps(data, indent=2)}\n"
            f"Major: {major}\n"
            f"Interests: {', '.join(interests) if interests else 'None'}\n"
            f"Years to Graduate: {years_to_graduate}\n"
            f"Max Credits per Semester: {max_credits}\n"
            f"Completed Courses: {', '.join(completed_courses) if completed_courses else 'None'}\n"
            "Please generate an optimized course schedule that maximizes efficiency by prioritizing prerequisites earlier. "
            "The student has already completed the listed courses, so they should NOT be included in the schedule. The interests represent the chosen minors"
            f"Given the minors curriculum:\n{json.dumps(minors_json, indent=2)}\n"
            f"Use this cirrciulum to add all the necessary course work based on the chosen interests. If a course in the selected interest already exist then DO NOT duplicate"
            f"Ensure the schedule is completed within {semesters} semesters if possible, and no semester exceeds the max credits allowed. "
            "Optimize the difficulty distribution, placing harder courses earlier while ensuring prerequisites are met first. "
            f"If it's not possible to meet the requirements within {semesters} semesters, provide the best possible alternative. ALWAYS start at semester 1"
            "Generate the course plan strictly in a JSON format with the following structure:\n"
            """
            {
                "AcademicPlan": [
                    {
                        "semester": "X Semester",
                        "credits": X,
                        "courses": [
                            {"CID": "Course Code", "credits": X},
                            {"CID": "Course Code", "credits": X}
                        ]
                    },
                    {
                        "semester": "X Semester",
                        "credits": X,
                        "courses": [
                            {"CID": "Course Code", "credits": X},
                            {"CID": "Course Code", "credits": X}
                        ]
                    }
                ]
            }
            """
            "Do NOT add any additional text or explanation—only return the JSON response."
        )

        # Generate the course plan using the API
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )

        # Extract response text
        response_text = response.text.strip()

        # Debugging: Print Gemini's raw response
        # st.write("Gemini Response:", response_text)

        # Extract only the JSON portion
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        cleaned_json_text = response_text[json_start:json_end]

        # Convert Gemini’s JSON-like string to a dictionary
        try:
            course_plan_json = json.loads(cleaned_json_text)
            return course_plan_json
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON format from Gemini: {e}")
            return None

    except Exception as e:
        st.error(f"Error generating course plan: {e}")
        return None


def display_course_plan(course_plan):
    """Processes and displays the course plan in separate tables for each semester using Streamlit."""
    if not course_plan:
        st.error("No course plan generated. Please try again.")
        return
    
    try:
        # Loop through each semester in the course plan
        st.subheader("📅 Your Optimized Course Plan")

        for semester in course_plan["AcademicPlan"]:
            # Flatten the course data for the current semester
            formatted_data = []
            for course in semester["courses"]:
                formatted_data.append({
                    "Course Code": course["CID"],
                    "Credits": round(course["credits"], 4)
                })

            # Convert to DataFrame
            df = pd.DataFrame(formatted_data)

            # Display the table for this semester
            st.subheader(f"{semester['semester']}")
            st.table(df)

    except Exception as e:
        st.error(f"Error displaying course plan: {e}")


def display_multiselect(items):
    """Displays a multi-select dropdown for selecting multiple items."""
    selected_items = st.multiselect("Select items:", items)
    return selected_items


def botGemini(question, data):
    """Queries the Gemini API with a given curriculum and user question."""
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=f"Based on this curriculum:\n{json.dumps(data, indent=2)}\n\n{question} answer in approximately 200-300 words/bullet points."
        )
        return response.text
    except Exception as e:
        st.error(f"Error querying Gemini API: {e}")
        return None
    


col1, col2, col3 = st.columns([1, 25, 1])

with col2:
    st.title("Courseflow")

    st.subheader("Tell us about your academic goals")
    major = st.selectbox("Select Your Major", majorsList)
    interest = st.multiselect("Select Interests (for minors/double majors)", minors_list)
    years_to_graduate = st.slider("Years to Graduate", 3, 5, 4)
    max_credits = st.slider("Max Credits Per Semester", 12, 21, 15)

    st.divider()

    # Load major-specific data
    data = load_major_data(major)
    if data:
        course_codes = extract_course_codes(data)

        st.subheader("📋 Select Completed Courses")
        completed_courses = display_multiselect(course_codes)

        st.divider()

        if "course_plan" not in st.session_state:
            st.session_state.course_plan = None

        if st.button("Generate Course Plan"):
            # Generate course plan using all selected inputs
            st.session_state.course_plan = generate_course_plan(
                data=data, 
                major=major, 
                interests=interest, 
                years_to_graduate=years_to_graduate, 
                max_credits=max_credits, 
                completed_courses=completed_courses
            )

            display_course_plan(st.session_state.course_plan)

        # Display the course plan if it's already in session_state
        if st.session_state.course_plan:
            display_course_plan(st.session_state.course_plan)

# Sidebar for Chatbot and State Session
with st.sidebar:
    st.subheader("💬 Chat with Your Course Plan")

    # Create a chat interface with a textbox and submit button
    chat_input = st.text_input("Ask a question about your course schedule")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("Submit Question"):
        if chat_input:
            # Clear previous question if any and add the new one
            st.session_state.chat_history = []

            # Simulate the response (replace this with real logic later)
            response = botGemini(chat_input, data)
            st.session_state.chat_history.append(response)

        else:
            st.warning("Please type a question to interact with your schedule.")

    # Display the chat history
    for message in st.session_state.chat_history:
        st.write(message)

    st.info("In the future, this will allow you to ask about professors, course preferences, etc.")

