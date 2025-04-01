import streamlit as st
from groq import Groq
from SPARQLWrapper import SPARQLWrapper, JSON
import tiktoken
import os
from dotenv import load_dotenv
from onto import get_drug_interactions , get_wikidata_id , visualize_graph
import matplotlib.pyplot as plt
import requests
import xml.etree.ElementTree as ET
import arxiv
from context_med import get_context 


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




def fetch_drug_context(drugs):
    """Fetch combined context for multiple drugs from DBpedia, Wikidata, and Google Knowledge Graph."""
    drug_contexts = []
    for drug in drugs.split(","):
        drug = drug.strip()  # Remove any extra whitespace
        drug_id = get_wikidata_id(drug)
        wikidata_context = get_drug_interactions(drug_id, drug)
        context_text = get_context(drug)
        drug_contexts.append(f"Drug: {drug}\n{wikidata_context}\n{context_text}")
    return "\n\n".join(drug_contexts)



def fetch_disease_context(disease):
    context = get_context(disease)
    return context

def analyze_data(user_details):
    """Fetch context and generate a patient report."""
    with st.spinner("🔍 Analyzing Data..."):

        # Fetch drug-specific context
        drug_context = fetch_drug_context(user_details["medications"]) + fetch_drug_context(user_details["prescribed_medicines"])
        disease_context = fetch_disease_context(user_details["current_disease"])

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

        Drug-Specific Context:{drug_context}
        Disease-Specific Context:{disease_context}
        """

        # Debugging: Display the combined context being sent to the LLM
        st.subheader("Context Sent to LLM:")
        st.code(combined_context, language="markdown")

        # Prompt for the LLM
        prompt = f"""
        You are a pharmacovigilance expert. Based on the following patient details and context, analyze the potential for adverse drug reactions (ADRs) and provide detailed insights and recommendations:
        {combined_context}
        """

        # Call the LLM to generate the report
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a pharmacovigilance expert."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile"
        )

        # Extract the LLM's response
        insights = response.choices[0].message.content

    # Display the report to the user
    st.success("✅ ADR Analysis Report Generated Successfully!")
    st.subheader("Adverse Drug Reaction Analysis Report 📝")
    st.write(insights)

    return insights  # Return insights for further use



def analyze_drug_interaction(user_details):
    """Visualize the interaction graph for each drug in the medications and prescribed medicines and display it in Streamlit."""
    st.header("🔗 Drug Interaction Visualization")
    medications = user_details["medications"] + "," + user_details["prescribed_medicines"]  # Combine medications and prescribed medicines
    for drug in medications.split(","):
        drug = drug.strip()  # Remove any extra whitespace
        if drug:  # Ensure the drug name is not empty
            try:
                drug_id = get_wikidata_id(drug)
                interactions = get_drug_interactions(drug_id, drug)
                if interactions:
                    plot = visualize_graph(interactions, drug)
                    st.pyplot(plot)  # Display the plot in Streamlit
                else:
                    st.warning(f"No interactions found for {drug}.")
            except ValueError as e:
                st.error(f"Error fetching data for {drug}: {e}")



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
        analyze_data(user_details)


        # Extract the first drug from each field
        analyze_drug_interaction(user_details)

        feedback = patient_feedback()
        if feedback:
            st.info("Your feedback will be used for deeper analysis.")
            user_details.update(feedback)
            st.write("Thank you for your feedback!")
    else:
        st.warning("Please complete all steps to proceed.")


if __name__ == "__main__":
    main()
