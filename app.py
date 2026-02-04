import streamlit as st
import pandas as pd
import json
from anthropic import Anthropic
import logging
from datetime import datetime, timedelta
import os

### Set up audit logging
logging.basicConfig(
    filename='hoos_who_audit.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def sanitize_input(user_input):
    """Sanitize user input to prevent injection attacks"""
    if not user_input or not isinstance(user_input, str):
        return ""
    
    # Remove potential script tags and SQL injection attempts
    dangerous_patterns = [
        '<script>', 'javascript:', 'onerror=', 'onclick=', 
        'DROP TABLE', 'DELETE FROM', 'INSERT INTO', 'SELECT *',
        '<iframe>', 'eval(', 'document.cookie'
    ]
    
    sanitized = user_input
    for pattern in dangerous_patterns:
        sanitized = sanitized.replace(pattern, '')
        sanitized = sanitized.replace(pattern.lower(), '')
        sanitized = sanitized.replace(pattern.upper(), '')
    
    # Limit length to prevent abuse
    return sanitized[:500]

def check_rate_limit():
    """Simple rate limiting - max 20 queries per hour per user"""
    if 'query_times' not in st.session_state:
        st.session_state.query_times = []
    
    # Remove queries older than 1 hour
    current_time = datetime.now()
    st.session_state.query_times = [
        t for t in st.session_state.query_times 
        if current_time - t < timedelta(hours=1)
    ]
    
    # Check if user has exceeded limit
    if len(st.session_state.query_times) >= 20:
        return False
    
    # Add current query time
    st.session_state.query_times.append(current_time)
    return True

def log_query(query_length, response_length, success=True):
    """Log queries for audit purposes (without storing actual content)"""
    status = "SUCCESS" if success else "FAILED"
    logging.info(f"Query - Status: {status}, Query Length: {query_length}, Response Length: {response_length}")

#UVA Color Scheme (Official Colors)
UVA_ORANGE = "#E57200"
UVA_NAVY = "#232D4B"
UVA_BLUE = "#0E4C92"
UVA_ROTUNDA = "#E8E9EA"

#Page config
st.set_page_config(
    page_title="Hoos Who? - UVA MSBA 2026 Network",
    page_icon="🔶",
    layout="wide",
    initial_sidebar_state="expanded"
)

#Function to stop auto-Streamlit reruns
@st.cache_data
def get_footer_html():
    """Returns the static HTML for the app footer."""
    return """
        <div style='text-align: center; margin-top: 3rem; padding: 2rem;'>
            <h3 style='color: #E57200; font-size: 2rem;'>Wahoowa! 🔶⚔️</h3>
            <p style='color: #666; font-style: italic;'>On the Lawn and in your corner</p>
        </div>
    """



#Custom CSS for enhanced UVA theming
st.markdown(f"""
    <style>
    /* Import Google Fonts for better typography */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap');
    
    * {{
        font-family: 'Montserrat', sans-serif;
    }}
    
    /* Main background (UVA Blue) */
    .main {{
        background: #232D4B" !important;
        background-color: #232D4B" !important;
    }}

    .stApp {{
    background: #232D4B" !important;
    background-color: #232D4B" !important;
}}
    
    /* Sidebar styling with UVA Navy gradient */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, {UVA_NAVY} 0%, #1a3a5c 100%);
    }}
    [data-testid="stSidebar"] * {{
        color: white !important;
    }}
    
    /* Button styling with hover effects */
    .stButton>button {{
        background: linear-gradient(135deg, {UVA_ORANGE} 0%, #ff8c1a 100%);
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.7rem 1.5rem;
        font-weight: 600;
        box-shadow: 0 4px 8px rgba(229, 114, 0, 0.3);
        transition: all 0.3s ease;
        font-size: 1rem;
    }}
    .stButton>button:hover {{
        background: linear-gradient(135deg, #c96100 0%, #e57200 100%);
        box-shadow: 0 6px 12px rgba(229, 114, 0, 0.5);
        transform: translateY(-2px);
    }}
    
    /* Header styling with text shadow */
    h1 {{
        color: white !important;
        font-weight: 700;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
        letter-spacing: -0.5px;
    }}
    h2, h3 {{
        color: white !important; /* CHANGED: Force white for main headers */
        font-weight: 600;
    }}
    
    /* Subtitle styling */
    .subtitle {{
        color: white !important; /* CHANGED: Force white for subtitle */
        font-size: 1.3rem;
        font-weight: 400;
        opacity: 0.8;
    }}

    /* --- NEW RULE --- */
    /* Force headers inside light-background elements back to navy */
    .welcome-card h1, .welcome-card h2, .welcome-card h3, .welcome-card .subtitle,
    .student-card h1, .student-card h2, .student-card h3,
    .assistant-message h1, .assistant-message h2, .assistant-message h3,
    .assistant-message .subtitle {{
        color: {UVA_NAVY} !important;
        opacity: 1;
    }}
    /* --- END NEW RULE --- */
    
    /* Chat message styling with animations */
    .chat-message {{
        padding: 1.3rem;
        border-radius: 15px;
        margin-bottom: 1.2rem;
        box-shadow: 0 3px 10px rgba(0,0,0,0.12);
        animation: fadeIn 0.4s ease;
    }}
    .user-message {{
        background: linear-gradient(135deg, {UVA_ORANGE} 0%, #ff8c1a 100%);
        color: white;
        border-left: 6px solid #c96100;
    }}
    .assistant-message {{
        background: white;
        border: 2px solid {UVA_NAVY};
        border-left: 6px solid {UVA_ORANGE};
        color: {UVA_NAVY};
    }}
    
    /* Student card styling with hover effect */
    .student-card {{
        background: white;
        padding: 1.3rem;
        border-radius: 12px;
        border-left: 6px solid {UVA_ORANGE};
        margin-bottom: 1rem;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
    }}
    .student-card:hover {{
        box-shadow: 0 6px 16px rgba(229, 114, 0, 0.2);
        transform: translateY(-4px);
        border-left-color: {UVA_NAVY};
    }}
    
    /* Welcome card with enhanced styling */
    .welcome-card {{
        background: rgba(255, 255, 255, 0.95);
        padding: 2.5rem;
        border-radius: 20px;
        border: 4px solid {UVA_ORANGE};
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
        margin-top: 2rem;
        text-align: center;
    }}
    
    /* Logo container */
    .logo-container {{
        text-align: center;
        padding: 1.5rem 1rem;
        margin-bottom: 1rem;
        background: linear-gradient(135deg, rgba(229,114,0,0.1) 0%, rgba(35,45,75,0.1) 100%);
        border-radius: 15px;
    }}
    
    /* Title with Cavalier styling */
    .main-title {{
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, {UVA_ORANGE} 0%, {UVA_NAVY} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.5rem;
    }}
    
    /* Stats badge */
    .stats-badge {{
        background: linear-gradient(135deg, {UVA_ORANGE} 0%, #ff8c1a 100%);
        color: white;
        padding: 0.6rem 1.2rem;
        border-radius: 25px;
        font-weight: 600;
        display: inline-block;
        margin: 0.5rem 0;
        box-shadow: 0 3px 6px rgba(229, 114, 0, 0.3);
    }}
    
    /* Animation keyframes */
    @keyframes fadeIn {{
        from {{ 
            opacity: 0; 
            transform: translateY(15px); 
        }}
        to {{ 
            opacity: 1; 
            transform: translateY(0); 
        }}
    }}
    
    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
    }}
    
    /* Chat input styling */
    .stChatInput {{
        border: 2px solid {UVA_ORANGE} !important;
        border-radius: 12px !important;
    }}
    
    /* Divider with UVA colors */
    hr {{
        border: none;
        height: 3px;
        background: linear-gradient(90deg, {UVA_ORANGE} 0%, {UVA_NAVY} 50%, {UVA_ORANGE} 100%);
        margin: 1.5rem 0;
    }}
    
    /* Emoji sizing */
    .big-emoji {{
        font-size: 4rem;
        line-height: 1;
        margin: 1rem 0;
    }}
    </style>
    """, unsafe_allow_html=True)

#Load student data
@st.cache_data
def load_student_data():
    return pd.read_csv('student_data.csv')

#Initialize Claude client
def get_claude_client():
    """Get Claude client with secure API key handling"""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    
    if not api_key:
        st.error("⚠️ API key not configured. Please contact administrator.")
        logging.error("API key missing - application cannot function")
        st.stop()
    
    return Anthropic(api_key=api_key)

#System prompt for Claude
SYSTEM_PROMPT = """You are "Hoos Who?" - a helpful assistant for UVA Darden MSBA students looking to connect with classmates based on career backgrounds.

You have access to a database of MSBA student profiles with their:
- Current company and role
- Past work experience
- Industries they've worked in
- Contact information
- Brief bios

When a user asks a question, search through the student data and provide helpful matches. Be friendly, concise, and always include:
1. Student name(s) that match their query
2. Why they're a good match
3. Their current role and company
4. Relevant past experience
5. How to contact them

If multiple students match, list the top 2-3 most relevant ones. Always maintain a friendly, collegial tone - these are classmates helping classmates!

Format your responses in a clear, scannable way. Use phrases like "Great question!" or "Here's who I'd recommend reaching out to:" to keep it conversational."""


def query_claude(user_question, student_data):
    """Query Claude with student data context - with error handling"""
    client = get_claude_client()
    
    # Convert student data to a readable format for Claude
    students_context = student_data.to_dict('records')
    context = json.dumps(students_context, indent=2)
    
    user_prompt = f"""Here's our current MSBA student database:

{context}

User question: {user_question}

Please search through the students and provide helpful recommendations for who they should connect with based on their question."""
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        response = message.content[0].text
        
        # Log successful query (without storing actual content)
        log_query(len(user_question), len(response), success=True)
        
        return response
        
    except Exception as e:
        # Log the actual error for admins
        logging.error(f"API Error: {str(e)}")
        log_query(len(user_question), 0, success=False)
        
        # Show generic message to users (don't leak system info)
        return "I'm having trouble processing your request right now. Please try again in a moment. If this continues, please contact support."

#Initialize session state for chat history
if 'messages' not in st.session_state:
    st.session_state.messages = []

# Sidebar with enhanced styling
with st.sidebar:
    # Logo/Header section
    st.markdown("""
        <div class="logo-container">
            <img src="https://report.honor.virginia.edu/sites/report.honor/files/uva_centrd_rgb_white.png" 
             style="width: 150px; margin-bottom: 1rem;">
            <h1 style='color: white; margin: 0; font-size: 2rem;'>Hoos Who?</h1>
            <p style='color: rgba(255,255,255,0.9); margin-top: 0.5rem; font-size: 0.9rem;'>UVA Darden MSBA 2026 Network</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("**How to use this chatbot:**")
    st.markdown("""
    Ask me questions like:
    - *Who works at ICF?*
    - *Who has government contracting/consulting experience?*
    - *Find me someone in the cohort who worked in tech and finance*
    - *Who should I talk to about breaking in finance or fintech?*
    """)
    
    st.markdown("---")
    
    # Load student data
    df = load_student_data()
    
    st.markdown(f"""
        <div style='text-align: center;'>
            <div class="stats-badge">{len(df)} Students</div>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("")
    
    # Company directory with search and alphabetized list
    with st.expander("**Company Directory**", expanded=False):
        # Get all unique companies and sort alphabetically
        all_companies = sorted(df['current_company'].unique())
        
        st.markdown(f"**{len(all_companies)} companies represented**")
        st.markdown("")
        
        # Search/filter
        search_term = st.text_input("🔍 Search companies:", "", key="company_search")
        
        # Filter companies based on search
        if search_term:
            filtered_companies = [c for c in all_companies if search_term.lower() in c.lower()]
        else:
            filtered_companies = all_companies
        
        st.markdown("---")
        
        # Display alphabetized list
        if filtered_companies:
            for company in filtered_companies:
                count = len(df[df['current_company'] == company])
                if count == 1:
                    st.markdown(f"• {company}")
                else:
                    st.markdown(f"• **{company}** ({count} students)")
        else:
            st.markdown("*No companies found matching your search*")
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([0.5, 3, 0.5])
    with col2:
        if st.button("🔄 Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    st.markdown("---")
    
    st.markdown("""
        <p style='text-align: center; font-size: 0.8rem; opacity: 0.7;'>
            Built by Hoos for fellow Hoos<br>
            Powered by Claude AI
        </p>
    """, unsafe_allow_html=True)

#Main content with enhanced header
st.markdown("""
    <div style='text-align: center; margin-bottom: 2rem;'>
        <div class="logo-container">
            <img src="https://brand.virginia.edu/sites/uva_brand/files/2023-07/71_UVALogo_2000x800.jpg" 
                 style="width: 120px; margin-bottom: 1rem;">
        </div>
        <h1 style='color: white; margin: 0; font-size: 2.5rem; font-weight: 800;'>Hoos Who?</h1>
        <p style='color: white; margin-top: 0.5rem; font-size: 1rem; line-height: 1.4rem;'>
            Identify and connect with your MSBA classmates working at your dream company or dream industry
        </p>
    </div>
""", unsafe_allow_html=True)


st.markdown("---")

import streamlit as st

# --- Initial State Setup ---
if 'shown_welcome' not in st.session_state:
    st.session_state.shown_welcome = False

# Career Services Modal Popup with UVA Imagery
@st.dialog("University of Virginia  |  Darden School of Business", width="large")
def show_career_services_modal():
    """Modal popup with career services reminder"""
    
    # 1. Apply global CSS styles for the modal background and centering
    st.markdown("""
        <style>
        /* Style the modal with sidebar colors */
        [data-testid="stDialog"] {
            background: linear-gradient(180deg, #232D4B 0%, #1a3a5c 100%);
        }
        [data-testid="stDialog"] * {
            color: white !important;
        }
        /* Target the internal container of the dialog for full centering */
        [data-testid="stVerticalBlock"] {
            text-align: center;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # --- Content Rendering using Native Streamlit Components ---
    
    # Logo: Wrapped in columns to force centering
    logo_col1, logo_col2, logo_col3, logo_col4, logo_col5, logo_col6, logo_col7, logo_col8, logo_col9, logo_col10 = st.columns([1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
    with logo_col5:
        st.image("https://media.cnn.com/api/v1/images/stellar/prod/200617130257-01-uva-reworked-logo-0616.jpg?q=x_0,y_0,h_1687,w_2997,c_fill/h_653,w_1160/f_avif", 
                 width=120)
    
    # Header and Introduction 
    st.markdown("<h2 style='color: white; margin-bottom: 1rem; font-size: 2rem;'>Welcome to Hoos Who?</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: white; font-size: 1.1rem; line-height: 1.6;'>Before you start exploring your classmate connections...</p>", unsafe_allow_html=True)

    # Message box with UVA Grounds background (Text is centered here)
    message_box_html = (
        "<div style='position: relative; padding: 2rem; border-radius: 15px; border: 3px solid #E57200; "
        "margin: 1.5rem 1rem; overflow: hidden;'>"
        
        # Background image layer
        "<div style='position: absolute; top: 0; left: 0; right: 0; bottom: 0;"
        "background-image: url(\"https://news.virginia.edu/sites/default/files/sunset_grounds_ss_18.jpg\");"
        "background-size: cover; background-position: center; opacity: 0.60; z-index: 0;'></div>"
        
        # Content layer (on top of background)
        "<div style='position: relative; z-index: 1; text-align: center;'>" 
        "<p style='color: white; font-size: 1.1rem; line-height: 1.7; margin: 0;'>"
        "<strong style='color: #E57200; font-size: 1.3rem;'> Have you met with Darden Career Services yet?</strong><br><br>"
        "Our career services professionals provide invaluable personalized advice, "
        "resume reviews, interview prep, and strategic guidance that AI cannot replace. "
        "They're extremely approachable and here to help!"
        "</p>"
        "</div>"
        "</div>"
    )
    st.markdown(message_box_html, unsafe_allow_html=True)

    # Link Button
    st.markdown("""
        <div style='text-align: center;'>
            <p>
                <a href='https://gtscandidate.mbafocus.com/Darden/Candidates/Authenticated/Advising/AdvisingAppointmentSignups.aspx' 
                   target='_blank' 
                   style='color: #E57200; 
                          font-weight: 600; 
                          text-decoration: none; 
                          font-size: 1.05rem;
                          padding: 0.75rem 1.5rem;
                          background: rgba(229, 114, 0, 0.2);
                          border-radius: 8px;
                          display: inline-block;
                          transition: all 0.3s ease;'>
                   📅 Schedule a time to meet with them →
                </a>
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    # Close button (Streamlit component)
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Got it! Let's explore", use_container_width=True, type="primary"):
            st.session_state.shown_welcome = True
            st.rerun()

# Show modal on first visit
if not st.session_state.shown_welcome:
    show_career_services_modal()

#Display chat history with enhanced styling
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
            <div class="chat-message user-message">
                <strong>You:</strong> {message["content"]}
            </div>
            """, unsafe_allow_html=True)
    else:
        #The assistant's message
        st.markdown(f"""
            <div class="chat-message assistant-message">
                <img src="https://1000logos.net/wp-content/uploads/2022/03/Virginia-Cavaliers-Logo.png" 
                     alt="UVA Logo" 
                     style="width: 40px; height: 40px; vertical-align: middle; margin-right: 5px;">
                <strong>
                    Hoos Who?:
                </strong>&nbsp;{message["content"]}
            </div>
        """, unsafe_allow_html=True)


# Chat input with security features
user_input = st.chat_input("Ask me anything about your classmates' backgrounds...")

if user_input:
    # Security Check 1: Sanitize input
    sanitized_input = sanitize_input(user_input)
    
    if not sanitized_input or len(sanitized_input) < 3:
        st.error("Invalid input. Please enter a valid question (at least 3 characters).")
        logging.warning(f"Invalid input rejected - length: {len(user_input)}")
        st.stop()
    
    # Security Check 2: Rate limiting
    if not check_rate_limit():
        st.warning("You've reached the hourly query limit (20 queries/hour). Please try again later.")
        logging.warning("Rate limit exceeded")
        st.stop()
    
    # Mark welcome modal as shown after first interaction
    if 'shown_welcome' in st.session_state:
        st.session_state.shown_welcome = True
    
    # Add user message to history
    st.session_state.messages.append({"role": "user", "content": sanitized_input})
    
    # Get Claude's response
    with st.spinner("🔍 Searching through your classmates..."):
        df = load_student_data()
        response = query_claude(sanitized_input, df)
    
    # Add assistant response to history
    st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Rerun to display new messages
    st.rerun()

#Welcome message if no chat history
if len(st.session_state.messages) == 0:
        st.markdown(f"""
    <div class="welcome-card" style=
        "background-image: linear-gradient(rgba(255,255,255,0.7), rgba(255,255,255,0.7)), /* CHANGED: Lowered opacity to 0.7 */
                          url('https://cdn.rbiva.com/wp-content/uploads/2020/06/RBI_Featured-Image_ConstuctionProject_UVARotunda.jpg');
        background-size: cover;
        background-position: center;
    ">
        <div class="big-emoji"></div>
            <h2 style="color: #232D4B; margin-bottom: 1rem; font-size: 2.2rem;">
    Welcome to: <span style="font-weight: 800; font-size: 2.4rem;">Hoos Who?</span>
</h2>
            <p style='color: #666; font-size: 1.15rem; line-height: 1.6;'>
                Your AI-powered guide to the UVA MSBA network!<br><br>
                Ask me anything about your classmates' work experience,<br>
                and I'll help you find the right people to connect with.
            </p>
            <p style='color: #E57200; font-size: 1rem; margin-top: 1.5rem; font-weight: 600;'>
                 Try asking: "Who has worked in finance?" or "Find me someone at FAANG or a similar tech company"
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    #Show sample student cards (example data)
st.markdown("<h3 style='margin-top: 2.5rem; text-align: center;'> Featured MSBA Classmates</h3>", unsafe_allow_html=True)
df = load_student_data()
sample_students = df.sample(min(3, len(df)))
    
cols = st.columns(3)
for idx, (_, student) in enumerate(sample_students.iterrows()):
    with cols[idx]:
        st.markdown(f"""
             <div class="student-card">
                 <h4 style="margin-bottom: 0.5rem; color: {UVA_NAVY}; font-size: 1.1rem;">{student['name']}</h4>
                <p style="color: {UVA_ORANGE}; font-weight: 600; margin-bottom: 0.7rem; font-size: 0.95rem;">
                      {student['current_role']}<br>@ {student['current_company']}
                </p>
                <p style="font-size: 0.85rem; color: #666; margin-bottom: 0.5rem;">
                   <strong>Past:</strong> {student['past_companies']}
                </p>
                 <p style="font-size: 0.8rem; color: #888;">
                    {student['industries']}
                 </p>
            </div>
            """, unsafe_allow_html=True)
    
#Wahoowa footer
st.markdown(get_footer_html(), unsafe_allow_html=True)
