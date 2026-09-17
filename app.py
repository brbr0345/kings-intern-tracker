import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="King's Intern Board", page_icon="📌", layout="wide")

# Real-time poll every 10 seconds
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

# Blocker Alert Banner
blocked = [t for t in tasks if t.get("status") == "Blocked / Need Help"]
if blocked:
    st.error(f"🚨 **{len(blocked)} Teammate(s) Blocked!** Immediate assistance needed:")
    for b in blocked:
        st.markdown(f"- **{b['assignee']}** (*{b['project']}*): {b.get('blocker_note', '')}")
else:
    st.success("✅ All projects are currently on track.")

st.divider()

# Create or Update Status Form
with st.expander("📝 Post or Update My Project Status", expanded=True):
    with st.form("status_form"):
        col1, col2 = st.columns(2)
        with col1:
            assignee = st.selectbox(
                "Your Name",
                ["Alex", "Jordan", "Taylor", "Morgan", "Sam", "Chris", 
                 "Pat", "Casey", "Riley", "Jamie", "Avery", "Dakota"]
            )
            project = st.text_input("Project / Workstream", placeholder="e.g., Bio/Biochem Needs Assessment")
            pin = st.text_input("Set or Enter Your 4-Digit PIN", type="password", max_chars=4, help="Only you can edit or delete this post with this PIN.")
            
        with col2:
            status = st.selectbox("Status", ["On Track", "Needs Review", "Blocked / Need Help"])
            blocker_note = st.text_area("Blocker Details", placeholder="Explain what is blocking you and what assistance you need.")

        if st.form_submit_button("Save Status"):
            if not project.strip():
                st.warning("Please specify a project name.")
            elif not pin.strip() or len(pin) < 4:
                st.warning("Please provide a 4-digit PIN to protect your post.")
            else:
                # Check if this assignee already has a record and verify PIN
                existing = [t for t in tasks if t["assignee"] == assignee]
                if existing and existing[0].get("pin") and existing[0]["pin"] != pin:
                    st.error("❌ Incorrect PIN. You are not authorized to edit this task.")
                else:
                    supabase.table("tasks").upsert({
                        "assignee": assignee,
                        "project": project,
                        "status": status,
                        "blocker_note": blocker_note if status == "Blocked / Need Help" else "",
                        "pin": pin
                    }, on_conflict="assignee").execute()
                    st.toast("Status saved successfully!")
                    st.rerun()

st.divider()

# Live Workflow Cards & Delete Actions
st.subheader("Team Workflows")
if not tasks:
    st.info("No active tasks. Use the form above to log your status.")
else:
    cols = st.columns(3)
    for i, t in enumerate(tasks):
        with cols[i % 3]:
            is_blocked = t.get("status") == "Blocked / Need Help"
            with st.container(border=True):
                st.markdown(f"### {t['assignee']}")
                st.caption(f"📁 **{t['project']}**")
                
                if is_blocked:
                    st.error(f"⚠️ **{t['status']}**")
                    st.write(f"*{t.get('blocker_note', '')}*")
                elif t.get("status") == "Needs Review":
                    st.warning(f"👀 {t['status']}")
                else:
                    st.success(f"🟢 {t['status']}")
                
                # Delete Popover Guard
                with st.popover("🗑️ Remove / Complete"):
                    st.write(f"Remove task for **{t['assignee']}**?")
                    delete_pin = st.text_input("Enter your 4-digit PIN to confirm", type="password", key=f"del_{t['assignee']}")
                    if st.button("Confirm Delete", key=f"btn_{t['assignee']}", type="primary"):
                        if t.get("pin") and delete_pin != t["pin"]:
                            st.error("Incorrect PIN!")
                        else:
                            supabase.table("tasks").delete().eq("assignee", t["assignee"]).execute()
                            st.toast("Task removed!")
                            st.rerun()