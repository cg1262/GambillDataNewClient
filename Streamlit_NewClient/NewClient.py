import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from openai import OpenAI
from datetime import datetime
import json
from azure.storage.blob import BlobServiceClient

# Setup
openai_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=openai_key)

# Email settings
EMAIL_SENDER = st.secrets["email"]["sender"]
EMAIL_PASSWORD = st.secrets["email"]["password"]
SMTP_SERVER = st.secrets["email"]["smtp_server"]
SMTP_PORT = st.secrets["email"]["smtp_port"]

#Blob information 
azure_conn_str = st.secrets["azure_blob"]["connection_string"]
container_name = st.secrets["azure_blob"]["container_name"]

# Calendly Link
CALENDLY_LINK = "https://calendly.com/chris-gambill-gambilldataengineering/data-consulting-initial-meeting"

def upload_to_azure_blob(data, filename):
    blob_service = BlobServiceClient.from_connection_string(azure_conn_str)
    blob_client = blob_service.get_blob_client(container=container_name, blob=filename)
    blob_client.upload_blob(json.dumps(data, indent=2), overwrite=True)


# --- PAGE SETUP ---
st.set_page_config(page_title="Client Discovery + Onboarding", layout="centered")
st.title("🚀 New Client Intake + Discovery")
st.write("Let’s get started by learning more about your business and goals.")

# --- Initialize session state properly ---
if "form_submitted" not in st.session_state:
    st.session_state.form_submitted = False
if "followup_done" not in st.session_state:
    st.session_state.followup_done = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "followup_1" not in st.session_state:
    st.session_state.followup_1 = None
if "answer_1" not in st.session_state:
    st.session_state.answer_1 = None
if "followup_2" not in st.session_state:
    st.session_state.followup_2 = None
if "answer_2" not in st.session_state:
    st.session_state.answer_2 = None

# --- Step 1: Client Form ---
with st.form("client_form"):
    name = st.text_input("Your name")
    email = st.text_input("Your email address")
    company = st.text_input("Company name")
    industry = st.selectbox("Industry", ["Tech", "Healthcare", "Finance", "Retail", "Nonprofit", "Other"])
    goals = st.text_area("What are your top data-related goals or problems?")
    services = st.multiselect("Services you're interested in", [
        "Data pipelines", "Dashboards", "Cloud migration", "Data warehouse", "Consulting", "Something else"])
    submit = st.form_submit_button("Submit & Start Discovery")

if submit:
    st.session_state.form_submitted = True
    st.success("✅ Thanks! Let’s ask a couple more questions to understand your needs better.")

# --- Step 2: GPT Follow-Up Chat ---
if st.session_state.form_submitted and not st.session_state.followup_done:

    # First GPT follow-up
    if st.session_state.followup_1 is None:
        prompt = f"As a data consultant, ask a thoughtful follow-up based on this business context: {goals}"
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        st.session_state.followup_1 = response.choices[0].message.content

    # Show first question
    if st.session_state.followup_1:
        answer_1 = st.text_area(f"🧠 {st.session_state.followup_1}", key="answer_1_field")
        if answer_1 and st.session_state.answer_1 is None:
            st.session_state.answer_1 = answer_1
            st.session_state.chat_history.append((st.session_state.followup_1, answer_1))

    # Second GPT follow-up
    if st.session_state.answer_1 and st.session_state.followup_2 is None:
        prompt2 = f"Based on this business context: {goals} and their answer: {st.session_state.answer_1}, ask one final clarifying question."
        response2 = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt2}],
            temperature=0.5
        )
        st.session_state.followup_2 = response2.choices[0].message.content

    # Show second question
    if st.session_state.followup_2:
        answer_2 = st.text_area(f"🔎 {st.session_state.followup_2}", key="answer_2_field")
        if answer_2 and st.session_state.answer_2 is None:
            st.session_state.answer_2 = answer_2
            st.session_state.chat_history.append((st.session_state.followup_2, answer_2))
            st.session_state.followup_done = True

# --- Step 3: Email + Calendly ---
if st.session_state.followup_done:
    st.success("✅ Thanks for sharing everything!")

    # Format email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"New Client Intake – {name}"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_SENDER

    chat_log = "\n\n".join([f"Q: {q}\nA: {a}" for q, a in st.session_state.chat_history])
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif;">
        <h2>🧾 New Client Intake Form</h2>
        <ul>
          <li><strong>Name:</strong> {name}</li>
          <li><strong>Email:</strong> {email}</li>
          <li><strong>Company:</strong> {company}</li>
          <li><strong>Industry:</strong> {industry}</li>
          <li><strong>Goals:</strong> {goals}</li>
          <li><strong>Services:</strong> {", ".join(services)}</li>
        </ul>

        <h3>🤖 GPT Discovery Chat</h3>
        <pre style="background-color:#f6f8fa;padding:10px;border-radius:5px;">{chat_log}</pre>

        <p><em>Submitted on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</em></p>
      </body>
    </html>
    """

    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.send_message(msg)
        st.success("📧 Your info was sent to Chris!")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

    # Calendly CTA
    st.markdown("### 🎯 Final Step: Book Your Discovery Call")
    st.markdown(f"[📅 Schedule Now]({CALENDLY_LINK})", unsafe_allow_html=True)

    result = {
        "timestamp": datetime.now().isoformat(),
        "request": {
            "name": name,
            "email": email,
            "company": company,
            "industry": industry,
            "goals": goals,
            "services": ", ".join(services), 
            "interests": chat_log
        } }
    #st.markdown(f"{result}")
    filename = f"new_client_{name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    upload_to_azure_blob(result, filename)
