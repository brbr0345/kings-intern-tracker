import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh

st.set_page_config(page_title="King's Intern Board", page_icon="📌", layout="wide")

# Poll for database changes every 10 seconds
st_autorefresh(interval=10 * 1000, key="datarefresh")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Load tasks: order ascending so older tasks stay on top and new tasks stack at the bottom
def fetch_tasks():
    response = supabase.table("tasks").select("*").order("updated_at", desc=False).execute()
    return response.data

tasks = fetch_tasks()

# Top Header Bar with Compact Add Button
if "show_form" not in st.session_state:
    st.session_state.show_form = False

header_col, btn_col = st.columns([5, 1])
with header_col:
    st.title("🎯 King's Center Intern Status Board")
with btn_col:
    st.write("") # Alignment spacing
    if st.button("➕ Add / Edit Task" if not st.session_state.show_form else "✖ Close Form", use_container_width=True):
        st.session_state.show_form = not st.session_state.show_form

# Blocker / Help Banner
needing_help = [t for t in tasks if t.get("status") == "Need Help"]
if needing_help:
    st.error(f"🚨 **{len(needing_help)} Teammate(s) Need Help:**")
    for item in needing_help:
        helpers_txt = f" (Needs {item['helpers_needed']} person/people)" if item.get("helpers_needed") else ""
        details_txt = f": {item['blocker_note']}" if item.get("blocker_note") else ""
        st.markdown(f"- **{item['assignee']}** on *{item['project']}*{helpers_txt}{details_txt}")
else:
    st.success("✅ All projects are currently on track.")

# Collapsed Add / Update Form (Expands only when button is clicked)
if st.session_state.show_form:
    with st.container(border=True):
        st.markdown("### 📝 New Task / Status Update")
        with st.form("task_form"):
            col1, col2 = st.columns(2)
            with col1:
                # Text input for name instead of dropdown
                assignee = st.text_input("Your Name", placeholder="e.g., Alex Kim")
                project = st.text_input("Project / Assignment", placeholder="e.g., Needs Assessment Survey Analysis")
                pin = st.text_input("4-Digit PIN", type="password", max_chars=4, help="Set a PIN so only you can edit or delete this post.")

            with col2:
                # Exactly two status choices
                status = st.radio("Status", ["On Track", "Need Help"], horizontal=True)
                
                helpers_needed = None
                blocker_note = ""
                if status == "Need Help":
                    helpers_needed = st.number_input(
                        "Number of people needed (optional - set 0 if not sure)", 
                        min_value=0, 
                        max_value=10, 
                        value=0, 
                        step=1
                    )
                    blocker_note = st.text_area("What do you need a hand with?", placeholder="Describe where you are stuck or what needs review...")

            submitted = st.form_submit_button("Post / Update Status", type="primary")
            if submitted:
                if not assignee.strip():
                    st.warning("Please enter your name.")
                elif not project.strip():
                    st.warning("Please enter a project name.")
                elif not pin.strip() or len(pin) < 4:
                    st.warning("Please enter a 4-digit PIN.")
                else:
                    # Verify PIN if updating an existing record
                    existing = [t for t in tasks if t["assignee"].strip().lower() == assignee.strip().lower()]
                    if existing and existing[0].get("pin") and existing[0]["pin"] != pin:
                        st.error("❌ Incorrect PIN. Only the original author can edit this post.")
                    else:
                        payload = {
                            "assignee": assignee.strip(),
                            "project": project.strip(),
                            "status": status,
                            "blocker_note": blocker_note if status == "Need Help" else "",
                            "helpers_needed": helpers_needed if (status == "Need Help" and helpers_needed > 0) else None,
                            "pin": pin
                        }
                        supabase.table("tasks").upsert(payload, on_conflict="assignee").execute()
                        st.session_state.show_form = False
                        st.rerun()

st.divider()

# Horizontal Task Rows (Stacking chronologically toward the bottom)
st.subheader("Active Tasks")
if not tasks:
    st.info("No tasks logged yet. Click '➕ Add / Edit Task' above to add the first one.")
else:
    for t in tasks:
        with st.container(border=True):
            col_name, col_proj, col_status, col_del = st.columns([2, 5, 3, 1])
            
            with col_name:
                st.markdown(f"**👤 {t['assignee']}**")
                
            with col_proj:
                st.markdown(f"**{t['project']}**")
                if t.get("status") == "Need Help" and t.get("blocker_note"):
                    st.caption(f"💬 {t['blocker_note']}")
                    
            with col_status:
                if t.get("status") == "Need Help":
                    tag = "🚨 Need Help"
                    if t.get("helpers_needed"):
                        tag += f" ({t['helpers_needed']} needed)"
                    st.error(tag)
                else:
                    st.success("🟢 On Track")
                    
            with col_del:
                with st.popover("🗑️"):
                    st.write(f"Delete entry for **{t['assignee']}**?")
                    del_pin = st.text_input("Enter 4-digit PIN", type="password", key=f"del_{t['assignee']}")
                    if st.button("Delete", key=f"btn_{t['assignee']}", type="primary"):
                        if t.get("pin") and del_pin != t["pin"]:
                            st.error("Incorrect PIN")
                        else:
                            supabase.table("tasks").delete().eq("assignee", t["assignee"]).execute()
                            st.toast("Task removed!")
                            st.rerun()