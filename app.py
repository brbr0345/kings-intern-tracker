import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

# Page setup
st.set_page_config(page_title="King's Intern Board", page_icon="📌", layout="wide")

# Poll database every 10 seconds for real-time sync across devices
st_autorefresh(interval=10 * 1000, key="datarefresh")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def fetch_tasks():
    response = supabase.table("tasks").select("*").order("updated_at", desc=True).execute()
    return response.data

tasks = fetch_tasks()

st.title("🎯 King's Center Intern Status & Blocker Board")

# Top Blocker Alert Banner
blocked = [t for t in tasks if t["status"] == "Blocked / Need Help"]
if blocked:
    st.error(f"🚨 **{len(blocked)} Teammate(s) Blocked!** Immediate assistance needed:")
    for b in blocked:
        st.markdown(f"- **{b['assignee']}** (*{b['project']}*): {b['blocker_note']}")
else:
    st.success("✅ All projects are currently on track.")

st.divider()

# Status Update Form
with st.expander("📝 Update My Status / Raise a Blocker", expanded=True):
    with st.form("status_form"):
        col1, col2 = st.columns(2)
        with col1:
            assignee = st.selectbox(
                "Your Name",
                ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", 
                 "Pat", "Casey", "Riley", "Jamie", "Avery", "Dakota"]
            )
            project = st.selectbox(
                "Project",
                [
                    "Bio/Biochem Needs Assessment & Survey",
                    "Pre-Health Admissions Data Analytics",
                    "Computational Biology Workshop Prep",
                    "Social Media & Outreach",
                    "Other / Custom Task"
                ]
            )
            if project == "Other / Custom Task":
                project = st.text_input("Specify Task Name", placeholder="Enter project name")
            
        with col2:
            status = st.selectbox("Status", ["On Track", "Needs Review", "Blocked / Need Help"])
            blocker_note = st.text_area(
                "Blocker Details", 
                placeholder="Explain what is blocking you and what assistance or resources you need."
            )

        if st.form_submit_button("Post / Update Status"):
            if not project.strip():
                st.warning("Please specify a project name.")
            else:
                supabase.table("tasks").upsert({
                    "assignee": assignee,
                    "project": project,
                    "status": status,
                    "blocker_note": blocker_note if status == "Blocked / Need Help" else "",
                }, on_conflict="assignee").execute()
                st.toast("Status updated successfully!")
                st.rerun()

st.divider()

# Live Workflow Cards
st.subheader("Team Workflows")
if not tasks:
    st.info("No status updates logged yet. Use the form above to add your first status.")
else:
    cols = st.columns(3)
    for i, t in enumerate(tasks):
        with cols[i % 3]:
            is_blocked = t["status"] == "Blocked / Need Help"
            with st.container(border=True):
                st.markdown(f"### {t['assignee']}")
                st.caption(f"📁 **{t['project']}**")
                if is_blocked:
                    st.error(f"⚠️ **{t['status']}**")
                    st.write(f"*{t['blocker_note']}*")
                elif t["status"] == "Needs Review":
                    st.warning(f"👀 {t['status']}")
                else:
                    st.success(f"🟢 {t['status']}")