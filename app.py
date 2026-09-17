import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import datetime

st.set_page_config(page_title="King's Intern Board", page_icon="📌", layout="wide")

# Live refresh every 10 seconds
st_autorefresh(interval=10 * 1000, key="datarefresh")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Helper to safely parse dates
def parse_date(val):
    if not val:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(str(val)[:10])
    except Exception:
        return datetime.date.today()

# Load tasks: older ones on top, new ones stacking at the bottom
def fetch_tasks():
    response = supabase.table("tasks").select("*").order("id", desc=False).execute()
    return response.data

tasks = fetch_tasks()

# Header Bar with Toggle Button
if "show_form" not in st.session_state:
    st.session_state.show_form = False

head_col, btn_col = st.columns([5, 1])
with head_col:
    st.title("🎯 King's Center Intern Status Board")
with btn_col:
    st.write("")
    if st.button("➕ Add Task" if not st.session_state.show_form else "✖ Close", use_container_width=True):
        st.session_state.show_form = not st.session_state.show_form

# Help / Blocker Alert Banner
needing_help = [t for t in tasks if t.get("status") == "Need Help"]
if needing_help:
    st.error(f"🚨 **{len(needing_help)} Teammate(s) Need Help:**")
    for item in needing_help:
        helpers_txt = f" (Needs {item['helpers_needed']} person/people)" if item.get("helpers_needed") else ""
        details_txt = f": {item['blocker_note']}" if item.get("blocker_note") else ""
        st.markdown(f"- **{item['assignee']}** on *{item['project']}*{helpers_txt}{details_txt}")
else:
    st.success("✅ All projects are currently on track.")

# Reactive Create Post Container
if st.session_state.show_form:
    with st.container(border=True):
        st.markdown("### 📝 Create New Post")
        col1, col2 = st.columns(2)
        with col1:
            assignee = st.text_input("Your Name", placeholder="e.g., Alex Kim", key="new_name")
            project = st.text_input("Project / Task Name", placeholder="e.g., Survey for King's Center programs", key="new_proj")
            post_date = st.date_input("Date Posted", value=datetime.date.today(), key="new_date")
            pin = st.text_input("Set 4-Digit PIN", type="password", max_chars=4, help="Required to edit or delete this post later.", key="new_pin")

        with col2:
            status = st.radio("Status", ["On Track", "Need Help"], horizontal=True, key="new_status")
            helpers_needed = None
            blocker_note = ""
            
            if status == "Need Help":
                # Starts completely blank and allows optional helper counts
                helpers_needed = st.number_input("Helpers needed (optional)", min_value=1, max_value=10, value=None, step=1, key="new_helpers")
                blocker_note = st.text_area("Need help with: (optional)", placeholder="Where are you stuck or what assistance do you need?", key="new_blocker")
            
            comments = st.text_area("Comments (optional)", placeholder="Any milestones, links, or notes for the team...", key="new_comments")

        if st.button("Publish Post", type="primary", key="publish_btn"):
            if not assignee.strip() or not project.strip():
                st.warning("Please enter both your name and project name.")
            elif not pin.strip() or len(pin) < 4:
                st.warning("Please set a 4-digit PIN.")
            else:
                supabase.table("tasks").insert({
                    "assignee": assignee.strip(),
                    "project": project.strip(),
                    "post_date": post_date.isoformat(),
                    "status": status,
                    "helpers_needed": helpers_needed if (status == "Need Help" and helpers_needed) else None,
                    "blocker_note": blocker_note.strip() if status == "Need Help" else "",
                    "comments": comments.strip(),
                    "pin": pin
                }).execute()
                st.session_state.show_form = False
                st.toast("Post added successfully!")
                st.rerun()

st.divider()

# Stacking Horizontal Rows
st.subheader("Active Tasks")
if not tasks:
    st.info("No tasks logged yet. Click '➕ Add Task' above to start.")
else:
    for t in tasks:
        parsed_dt = parse_date(t.get("post_date"))
        date_str = parsed_dt.strftime("%b %d, %Y")
        
        with st.container(border=True):
            col_date, col_name, col_proj, col_status, col_actions = st.columns([1.5, 2, 4.5, 2.5, 1.5])
            
            with col_date:
                st.caption("POSTED")
                st.markdown(f"🗓️ **{date_str}**")

            with col_name:
                st.caption("ASSIGNEE")
                st.markdown(f"**👤 {t['assignee']}**")

            with col_proj:
                st.caption("PROJECT & NOTES")
                st.markdown(f"**{t['project']}**")
                if t.get("status") == "Need Help" and t.get("blocker_note"):
                    st.error(f"⚠️ **Help needed:** {t['blocker_note']}")
                if t.get("comments"):
                    st.caption(f"💬 {t['comments']}")

            with col_status:
                st.caption("STATUS")
                if t.get("status") == "Need Help":
                    tag = "🚨 Need Help"
                    if t.get("helpers_needed"):
                        tag += f" ({t['helpers_needed']} needed)"
                    st.error(tag)
                else:
                    st.success("🟢 On Track")

            with col_actions:
                st.caption("ACTIONS")
                act_c1, act_c2 = st.columns(2)
                
                # Full Edit Popover (PIN Protected)
                with act_c1.popover("✏️"):
                    st.markdown(f"**Edit Post**")
                    with st.form(key=f"edit_form_{t['id']}"):
                        edit_pin = st.text_input("Enter 4-Digit PIN to authorize", type="password", key=f"p_{t['id']}")
                        edit_name = st.text_input("Name", value=t.get("assignee", ""), key=f"n_{t['id']}")
                        edit_project = st.text_input("Project", value=t.get("project", ""), key=f"pr_{t['id']}")
                        edit_date = st.date_input("Post Date", value=parsed_dt, key=f"d_{t['id']}")
                        
                        edit_status = st.radio("Status", ["On Track", "Need Help"], index=0 if t.get("status") == "On Track" else 1, horizontal=True, key=f"st_{t['id']}")
                        edit_helpers = st.number_input(
                            "Helpers needed (optional)", 
                            min_value=1, 
                            max_value=10, 
                            value=int(t.get("helpers_needed")) if t.get("helpers_needed") else None, 
                            step=1, 
                            key=f"h_{t['id']}"
                        )
                        edit_blocker = st.text_area("Need help with: (optional)", value=t.get("blocker_note") or "", key=f"bn_{t['id']}")
                        edit_comments = st.text_area("Comments (optional)", value=t.get("comments") or "", key=f"c_{t['id']}")

                        if st.form_submit_button("Save Changes", type="primary"):
                            if t.get("pin") and edit_pin != t["pin"]:
                                st.error("❌ Incorrect PIN. Unauthorized.")
                            elif not edit_name.strip() or not edit_project.strip():
                                st.warning("Name and project cannot be blank.")
                            else:
                                supabase.table("tasks").update({
                                    "assignee": edit_name.strip(),
                                    "project": edit_project.strip(),
                                    "post_date": edit_date.isoformat(),
                                    "status": edit_status,
                                    "helpers_needed": edit_helpers if (edit_status == "Need Help" and edit_helpers) else None,
                                    "blocker_note": edit_blocker.strip() if edit_status == "Need Help" else "",
                                    "comments": edit_comments.strip()
                                }).eq("id", t["id"]).execute()
                                st.toast("Task updated!")
                                st.rerun()

                # Delete Popover (PIN Protected)
                with act_c2.popover("🗑️"):
                    st.write("Delete post?")
                    del_pin = st.text_input("PIN", type="password", key=f"del_pin_{t['id']}")
                    if st.button("Confirm", key=f"del_btn_{t['id']}", type="primary"):
                        if t.get("pin") and del_pin != t["pin"]:
                            st.error("Wrong PIN")
                        else:
                            supabase.table("tasks").delete().eq("id", t["id"]).execute()
                            st.toast("Deleted!")
                            st.rerun()