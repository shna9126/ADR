import streamlit as st
from groq import Groq
import os
from dotenv import load_dotenv
from preprocess import yake_keywords
from PIL import Image
from context_med import get_dbpedia_interactions, get_wikidata_interactions, get_google_kg_interactions  # Import functions
from onto import get_interaction_report, visualize_interaction
import matplotlib.pyplot as plt
import requests
import xml.etree.ElementTree as ET
import arxiv

# Load environment variables
load_dotenv()
key = os.getenv('API_KEY')
if not key:
    st.error("API key is missing. Please set the API_KEY in your .env file.")
    st.stop()

client = Groq(api_key=key)

# Maximum file size for upload (in MB)
MAX_FILE_SIZE_MB = 5

# Custom CSS for transparent background image
st.markdown("""
    <style>
        /* Transparent background image spanning the full page */
        .stApp {
            background: url('https://img.freepik.com/free-photo/medicine-capsules-global-health-with-geometric-pattern-digital-remix_53876-126742.jpg') no-repeat center center fixed;
            background-size: cover;
            opacity: 1; /* Adjust transparency */
        }
        .main {
            background-color: rgba(255, 255, 255, 0.85); /* Slightly opaque white background */
            padding: 20px;
            border-radius: 10px;
        }
        .stButton>button {
            background-color: #008CBA; 
            color: white; 
            border-radius: 5px;
        }
        .stTextInput, .stTextArea, .stNumberInput, .stSelectbox {
            border-radius: 5px;
        }
        /* Set text color to black for the main app */
        body, .stApp, .main, .stMarkdown {
            color: black;
        }
        /* Set text color to white for the entire sidebar */
        [data-testid="stSidebar"] * {
            color: white !important;
        }
    </style>
""", unsafe_allow_html=True)


def calculate_bmi(weight, height):
    """Calculate BMI and return the value along with its category."""
    if height > 0:
        bmi = weight / ((height / 100) ** 2)  # Convert height to meters
        if bmi < 18.5:
            category = "Underweight"
        elif 18.5 <= bmi < 24.9:
            category = "Normal weight"
        elif 25 <= bmi < 29.9:
            category = "Overweight"
        else:
            category = "Obesity"
        return round(bmi, 2), category
    return None, "Invalid height"

def enter_details():
    """Collect user details with better UI design."""
    st.header("🩺 Patient Information")
    with st.expander("Step 1: Fill in your basic details 👇", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name:")
            age = st.number_input("Age:", min_value=0, max_value=120, step=1)
            gender = st.radio("Gender:", ["Male", "Female"], horizontal=True)
        with col2:
            phone_number = st.text_input("Phone Number:")
            email = st.text_input("Email Address:")

        weight = st.number_input("Weight (kg):", min_value=0.0, max_value=500.0, step=0.1)
        height = st.number_input("Height (cm):", min_value=0.0, max_value=300.0, step=0.1)

        if weight > 0 and height > 0:
            bmi, category = calculate_bmi(weight, height)
            st.metric(label="Your BMI", value=f"{bmi} ({category})")

    with st.expander("Step 2: Fill in your medical history 👇"):
        allergies = st.text_area("Allergies:")
        medications = st.text_area("Ongoing Medications (Include duration and medicine name):")
        tests = st.text_area("Tests undergone (Include last tested metric):")

    with st.expander("Step 3: Enter current diagnosis 👇"):
        current_disease = st.text_input("Current Disease Detected:")
        medical_tests = st.text_area("Medical Tests Done:")
        hospital_name = st.text_input("Name of Hospital:")
        doctor_qualification = st.text_input("Doctor's Qualification:")
        prescribed_medicines = st.text_area("Medicines Prescribed:")

    if st.button("✅ Submit Details"):
        return {
            "name": name, "age": age, "gender": gender, "phone": phone_number, "email": email,
            "weight": weight, "height": height, "bmi": bmi, "bmi_category": category,
            "allergies": allergies, "medications": medications, "tests": tests,
            "current_disease": current_disease, "medical_tests": medical_tests,
            "hospital_name": hospital_name, "doctor_qualification": doctor_qualification,
            "prescribed_medicines": prescribed_medicines
        }
    return None

def patient_feedback():
    """Collect patient feedback for deeper analysis."""
    st.header("📝 Patient Feedback")
    with st.expander("Step 4: Provide your feedback 👇", expanded=True):
        feedback = st.text_area("Share your feedback about the diagnosis and treatment:")
        additional_results = st.text_area("Provide any additional results or observations:")
        if st.button("Submit Feedback"):
            st.success("✅ Feedback submitted successfully!")
            return {"feedback": feedback, "additional_results": additional_results}
    return None

def process_uploaded_image(uploaded_file):
    """Handle image conversion and compression."""
    if uploaded_file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        st.error(f"File too large! Max size: {MAX_FILE_SIZE_MB}MB.")
        return None

    try:
        image = Image.open(uploaded_file)
        compressed_path = f"compressed_{uploaded_file.name}"
        image.save(compressed_path, "JPEG", optimize=True, quality=70)
        return compressed_path
    except Exception as e:
        st.error(f"Image processing failed: {e}")
        return None


def fetch_combined_context(drug):
    """Fetch combined context from DBpedia, Wikidata, and Google Knowledge Graph."""
    dbpedia_context = get_dbpedia_interactions(drug)
    wikidata_context = get_wikidata_interactions(drug)
    google_kg_context = get_google_kg_interactions(drug)

    combined_context = {
        "DBpedia": dbpedia_context,
        "Wikidata": wikidata_context,
        "GoogleKG": google_kg_context,
    }

    return combined_context

def get_arxiv_context(query):
    """Fetch research papers from Arxiv based on a query using the arxiv library."""
    try:
        search = arxiv.Search(
            query=query,
            max_results=5,  # Limit the number of results
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        papers = []
        for result in search.results():
            papers.append({
                "title": result.title,
                "summary": result.summary,
                "link": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d")
            })
        return papers
    except Exception as e:
        print(f"Arxiv API request failed: {e}")
        return []

def analyze_image(image_path, user_details):
    """Fetch context and generate a patient report."""
    with st.spinner("🔍 Analyzing Data..."):
        # Fetch drug-specific context
        drug_context = fetch_combined_context(user_details["current_disease"])
        arxiv_context = get_arxiv_context(user_details["current_disease"])

        # Combine all user details and additional context
        combined_context = f"""
        Patient Details:
        Name: {user_details['name']}
        Age: {user_details['age']}
        Gender: {user_details['gender']}
        Phone: {user_details['phone']}
        Email: {user_details['email']}
        Weight: {user_details['weight']} kg
        Height: {user_details['height']} cm
        BMI: {user_details['bmi']} ({user_details['bmi_category']})

        Medical History:
        Allergies: {user_details['allergies']}
        Medications: {user_details['medications']}
        Tests: {user_details['tests']}

        Current Diagnosis:
        Disease Detected: {user_details['current_disease']}
        Medical Tests Done: {user_details['medical_tests']}
        Hospital Name: {user_details['hospital_name']}
        Doctor's Qualification: {user_details['doctor_qualification']}
        Prescribed Medicines: {user_details['prescribed_medicines']}

        Feedback:
        {user_details.get('feedback', 'No feedback provided.')}

        Drug-Specific Context:
        DBpedia: {', '.join(drug_context['DBpedia']) if drug_context['DBpedia'] else 'No context found.'}
        Wikidata: {', '.join(drug_context['Wikidata']) if drug_context['Wikidata'] else 'No context found.'}
        Arxiv: {', '.join([paper['title'] for paper in arxiv_context]) if arxiv_context else 'No context found.'}
        """

        # Debugging: Display the combined context being sent to the LLM
        st.subheader("Context Sent to LLM:")
        st.code(combined_context, language="markdown")

        # Prompt for the LLM
        prompt = f"""
        You are a medical assistant. Based on the following patient details and context, generate a detailed patient report with health insights and recommendations:
        {combined_context}
        """

        # Call the LLM to generate the report
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a medical assistant."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )

        # Extract the LLM's response
        insights = response.choices[0].message.content

    # Display the report to the user
    st.success("✅ Report Generated Successfully!")
    st.subheader("Patient Report 📝")
    st.write(insights)

    return insights  # Return insights for further use

def analyze_drug_interaction(drug_a, drug_b):
    """Analyze the interaction between two drugs and visualize the results."""
    st.header("💊 Drug Interaction Analysis")

    if not drug_a or not drug_b:
        st.error("Please ensure both drug names are provided.")
        return

    # Get the interaction report
    with st.spinner("🔍 Analyzing drug interactions..."):
        report = get_interaction_report(drug_a, drug_b)

    # Display the interaction report
    st.subheader("Interaction Report")
    st.write(f"**Drugs Analyzed:** {drug_a} and {drug_b}")
    st.write(f"**Direct Interaction:** {'Yes' if report['direct'] else 'No'}")
    st.write(f"**Shared Interactions:** {', '.join(report['common']) if report['common'] else 'None'}")

    # Visualize the interaction
    st.subheader("Interaction Visualization")
    with st.spinner("🔍 Generating visualization..."):
        fig, ax = plt.subplots(figsize=(12, 8))
        visualize_interaction(report)  # Generate the visualization
        st.pyplot(fig)

    # Generate deeper analysis
    deeper_analysis = f"""
    **Deeper Analysis:**
    - The drugs {drug_a} and {drug_b} {'have' if report['direct'] else 'do not have'} a direct interaction.
    - Shared interactions: {', '.join(report['common']) if report['common'] else 'None'}.
    - Neighboring drugs for {drug_a}: {', '.join(report['neighbors_a']) if report['neighbors_a'] else 'None'}.
    - Neighboring drugs for {drug_b}: {', '.join(report['neighbors_b']) if report['neighbors_b'] else 'None'}.
    """
    st.subheader("Deeper Analysis")
    st.write(deeper_analysis)


def main():
    """Main Streamlit app function with improved UI."""
    st.title("🏥 Health Recommendation System")
    st.sidebar.title("Navigation")
    st.sidebar.markdown("""
        ### Steps to Follow:
        1. **Enter Basic Details**: Provide your contact details, height, weight, and calculate BMI.
        2. **Fill Medical History**: Add details about medications, tests, and medical history.
        3. **Enter Current Diagnosis**: Provide information about your current disease, tests, hospital, and doctor.
        4. **Analyze Drug Interactions**: Check the interaction between two drugs.
        5. **Provide Feedback**: Share your feedback and results for deeper analysis.
    """)

    # Collect user details
    user_details = enter_details()
    if user_details:
        st.success("✅ Basic details submitted successfully!")

        # Process the data and generate the report immediately after submission
        insights = analyze_image(None, user_details)

        # Extract drug names from user details
        ongoing_medications = user_details.get("medications", "")
        prescribed_medicines = user_details.get("prescribed_medicines", "")

        # Extract the first drug from each field
        drug_a = ongoing_medications.split(",")[0].strip() if ongoing_medications else None
        drug_b = prescribed_medicines.split(",")[0].strip() if prescribed_medicines else None

        # Drug interaction analysis
        if drug_a and drug_b:
            analyze_drug_interaction(drug_a, drug_b)
        else:
            st.warning("Unable to analyze drug interactions. Please ensure both fields are filled.")

        # Ask for feedback after displaying the report
        feedback = patient_feedback()
        if feedback:
            st.info("Your feedback will be used for deeper analysis.")
            user_details.update(feedback)
            st.write("Thank you for your feedback!")
    else:
        st.warning("Please complete all steps to proceed.")


if __name__ == "__main__":
    main()
