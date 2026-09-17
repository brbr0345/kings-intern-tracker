import streamlit as st
from supabase import create_client
from streamlit_autorefresh import st_autorefresh
import datetime

st.set_page_config(page_title="King's Intern Board", page_icon="📌", layout="wide")

# CSS: Force-center helper stepper number and hide Streamlit footer / badges
st.markdown(
    """
    <style>
    /* Force-center the stepper number input */
    div[data-testid="stTextInput"] input[aria-label*="Helpers needed"],
    input[aria-label*="Helpers needed"] {
        text-align: center !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
    }
    /* Completely removes Streamlit footer, badge, and creator handle link */
    footer {visibility: hidden !important; display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    div[class*="viewerBadge"] {display: none !important;}
    a[href*="share.streamlit.io"] {display: none !important;}
    </style>
    """,
    unsafe_allow_html=True
)

# Live refresh every 10 seconds
st_autorefresh(interval=10 * 1000, key="datarefresh")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

# Cache tasks query: desc=True ensures newest tasks stack at the top
@st.cache_data(ttl=10)
def fetch_tasks():
    response = supabase.table("tasks").select("*").order("id", desc=True).execute()
    return response.data

tasks = fetch_tasks()

# Safe date parsing
def parse_date(val):
    if not val:
        return datetime.date.today()
    try:
        return datetime.date.fromisoformat(str(val)[:10])
    except Exception:
        return datetime.date.today()

# Helper stepper state management
if "new_helpers_val" not in st.session_state:
    st.session_state.new_helpers_val = ""

def dec_helpers():
    val = str(st.session_state.get("new_helpers_val", "")).strip()
    if val.isdigit():
        n = int(val) - 1
        st.session_state.new_helpers_val = str(n) if n > 0 else ""
    else:
        st.session_state.new_helpers_val = ""

def inc_helpers():
    val = str(st.session_state.get("new_helpers_val", "")).strip()
    if val.isdigit():
        st.session_state.new_helpers_val = str(int(val) + 1)
    else:
        st.session_state.new_helpers_val = "1"

if "show_form" not in st.session_state:
    st.session_state.show_form = False

def toggle_form():
    st.session_state.show_form = not st.session_state.show_form

# Fragment decorator to isolate reruns so +/- updates instantly
fragment = st.fragment if hasattr(st, "fragment") else (lambda f: f)

@fragment
def render_header_and_form():
    head_col, btn_col = st.columns([5, 1])
    with head_col:
        st.title("🎯 King's Center Intern Status Board")
    with btn_col:
        st.write("")
        btn_label = "✖ Close" if st.session_state.show_form else "➕ Add Task"
        st.button(btn_label, on_click=toggle_form, use_container_width=True)

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
                blocker_note = ""
                
                if status == "Need Help":
                    st.write("**Helpers needed (optional)**")
                    h_sub, h_in, h_add, _ = st.columns([0.4, 0.9, 0.4, 2.3])
                    with h_sub:
                        st.button("➖", on_click=dec_helpers, key="btn_dec_h", use_container_width=True)
                    with h_in:
                        st.text_input(
                            "Helpers needed (optional)",
                            key="new_helpers_val",
                            placeholder="",
                            label_visibility="collapsed"
                        )
                    with h_add:
                        st.button("➕", on_click=inc_helpers, key="btn_inc_h", use_container_width=True)

                    blocker_note = st.text_area("Need help with: (optional)", placeholder="Where are you stuck or what assistance do you need?", key="new_blocker")
                
                comments = st.text_area("Comments (optional)", placeholder="Any milestones, links, or notes for the team...", key="new_comments")

            if st.button("Publish Post", type="primary", key="publish_btn"):
                helpers_str = str(st.session_state.get("new_helpers_val", "")).strip()
                helpers_needed = int(helpers_str) if (status == "Need Help" and helpers_str.isdigit() and int(helpers_str) > 0) else None

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
                        "helpers_needed": helpers_needed,
                        "blocker_note": blocker_note.strip() if status == "Need Help" else "",
                        "comments": comments.strip(),
                        "pin": pin
                    }).execute()
                    fetch_tasks.clear()
                    st.session_state.new_helpers_val = ""
                    st.session_state.show_form = False
                    st.toast("Post added successfully!")
                    try:
                        st.rerun(scope="app")
                    except TypeError:
                        st.rerun()

render_header_and_form()

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

st.divider()

# Stacking Horizontal Rows (Newest on Top)
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
                act_c1, act_c2 = st.columns(2)
                
                # Full Edit Popover (PIN Protected)
                with act_c1.popover("✏️"):
                    st.markdown("**Edit Post**")
                    with st.form(key=f"edit_form_{t['id']}"):
                        edit_pin = st.text_input("Enter 4-Digit PIN to authorize", type="password", key=f"p_{t['id']}")
                        edit_name = st.text_input("Name", value=t.get("assignee", ""), key=f"n_{t['id']}")
                        edit_project = st.text_input("Project", value=t.get("project", ""), key=f"pr_{t['id']}")
                        edit_date = st.date_input("Post Date", value=parsed_dt, key=f"d_{t['id']}")
                        
                        edit_status = st.radio("Status", ["On Track", "Need Help"], index=0 if t.get("status") == "On Track" else 1, horizontal=True, key=f"st_{t['id']}")
                        
                        edit_h_col, _ = st.columns([1.2, 1.8])
                        with edit_h_col:
                            edit_helpers = st.number_input(
                                "Helpers needed (optional)", 
                                min_value=0, 
                                max_value=10, 
                                value=int(t.get("helpers_needed")) if t.get("helpers_needed") else 0, 
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
                                    "helpers_needed": edit_helpers if (edit_status == "Need Help" and edit_helpers > 0) else None,
                                    "blocker_note": edit_blocker.strip() if edit_status == "Need Help" else "",
                                    "comments": edit_comments.strip()
                                }).eq("id", t["id"]).execute()
                                fetch_tasks.clear()
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
                            fetch_tasks.clear()
                            st.toast("Deleted!")
                            st.rerun()