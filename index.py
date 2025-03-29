import streamlit as st
from google import genai
import json
import os
from dotenv import load_dotenv
load_dotenv()

# Centering content and text alignment
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
st.title("🎓 Build Your College Plan")
st.subheader("Tell us about your academic goals")

# Gemini API
client = genai.Client(api_key=os.getenv("API_KEY"))

majorDict = {
    "Computer Engineering" : "cmpen.json",
    "Aerospace Engineering" : "aero.json",
    "Chemical Engineering" : "chemeg.json",
    "Civil Engineering" : "civeng.json",
    "Computational Data Sciences" : "cmpds.json",
    "Computer Science" : "cmpsc.json",
    "Electrical Engineering" : "EEng.json",
    "Engineering Sciences" : "engsci.json",
    "Industrial Engineering" : "indeng.json",
    "Nuclear Engineering" : "NucEng.json"
}

majorsList = []
for major in majorDict.keys():
    majorsList.append(major)




def extract_course_codes(json_data):
    course_codes = []

    def traverse(obj, in_valid_semester=False):
        if isinstance(obj, dict):
            # Check if the key itself is "1st Semester" or "2nd Semester"
            if "1st Semester" in obj or "2nd Semester" in obj:
                traverse(obj.get("1st Semester", {}), True)
                traverse(obj.get("2nd Semester", {}), True)

            for key, value in obj.items():
                # If we find a semester key, mark it as valid for traversal
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

# Use json data
with open("cmpen.json", "r") as file:
    data = json.load(file)
    course_codes = extract_course_codes(data)


def query_gemini(question):

    response = client.models.generate_content(
    model="gemini-2.0-flash", contents=f"Based on this curriculum:\n{data}\n\n{question}"
    )

    return response.text

def geminiQuestion():
    response = client.models.generate_content(
        model = "gemini-2.0-flash", contents = f"Given the major {data} provide me only a horizontal table of all courses per semester and credits for a student. Do 2 semesters per row. Also manipulate the courses such that it only takes 6 semesters to complete all courses. Keep in mind any prerequisites that would be necessary. Make sure that the max credits does not go over 21 otherwise tell the student that their plan is not possible."
    )

    st.write(response.text)


def display_checkboxes(items):
    selected_items = []
    
    for idx, item in enumerate(items):
        if st.checkbox(item, key=f"checkbox_{idx}"):  # Use a unique key for each checkbox
            selected_items.append(item)
    
    return selected_items




# Create centered columns
col1, col2, col3 = st.columns([1, 8, 1])
with col2:
    major = st.selectbox("Select Your Major", majorsList)
    interest = st.multiselect("Select Interests (for minors/double majors)", [])
    years_to_graduate = st.slider("Years to Graduate", 3, 5, 4)
    max_credits = st.slider("Max Credits Per Semester", 12, 21, 15)
    
    # Completed Courses
    st.subheader("📋 Select Completed Courses")
    selected_courses = display_checkboxes(course_codes)
    completed_courses = [course for course in selected_courses if st.checkbox(course, key=course)]
    
    if st.button("Generate Course Plan"):
        st.subheader("📅 Your Personalized Course Plan")
        geminiQuestion()

    
    
    