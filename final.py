"""
AI Tutor Platform v2.0 - FULLY WORKING VERSION
Complete with: Authentication, Dark/Light Theme, Enhanced Dashboard, Visual Learning
Author: AI Tutor Team
"""

import gradio as gr
import json
import hashlib
from datetime import datetime
from groq import Groq
import sqlite3

# ==================== DATABASE SETUP ====================
DB_PATH = "ai_tutor.db"

def init_database():
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT NOT NULL,
            activity_type TEXT,
            content TEXT,
            quiz_score TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            user_id INTEGER PRIMARY KEY,
            api_key TEXT,
            theme TEXT DEFAULT 'light',
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password, email=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
            (username, password_hash, email)
        )
        
        user_id = cursor.lastrowid
        cursor.execute(
            "INSERT INTO user_settings (user_id, theme) VALUES (?, 'light')",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
        return True, "✅ Account created! Please sign in."
    except sqlite3.IntegrityError:
        return False, "⚠️ Username exists. Choose another."
    except Exception as e:
        return False, f"⚠️ Error: {str(e)}"

def verify_user(username, password):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        password_hash = hash_password(password)
        cursor.execute(
            "SELECT id, username FROM users WHERE username = ? AND password_hash = ?",
            (username, password_hash)
        )
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return True, user[0], user[1]
        return False, None, None
    except:
        return False, None, None

def save_to_history(user_id, topic, activity_type, content, quiz_score=""):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO learning_history (user_id, topic, activity_type, content, quiz_score) VALUES (?, ?, ?, ?, ?)",
            (user_id, topic, activity_type, content[:500], quiz_score)
        )
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def get_user_history(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT topic, activity_type, quiz_score, timestamp FROM learning_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 50",
            (user_id,)
        )
        
        history = cursor.fetchall()
        conn.close()
        
        if not history:
            return "### 📚 No learning history yet\n\nStart learning to build your history!"
        
        text = "## 📚 Your Learning History\n\n"
        for topic, activity, score, timestamp in history:
            time_str = datetime.fromisoformat(timestamp).strftime("%b %d, %Y %H:%M")
            
            if activity == "quiz":
                text += f"- 🎯 **{topic}** - Quiz: {score} - *{time_str}*\n"
            elif activity == "explanation":
                text += f"- 📖 **{topic}** - Studied - *{time_str}*\n"
            elif activity == "examples":
                text += f"- 💡 **{topic}** - Examples - *{time_str}*\n"
            elif activity == "summary":
                text += f"- 📊 **{topic}** - Summary - *{time_str}*\n"
        
        return text
    except Exception as e:
        return f"Error: {str(e)}"

def get_user_settings(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT api_key, theme FROM user_settings WHERE user_id = ?", (user_id,))
        settings = cursor.fetchone()
        conn.close()
        
        if settings:
            return settings[0] or "", settings[1] or "light"
        return "", "light"
    except:
        return "", "light"

def update_user_settings(user_id, api_key, theme):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE user_settings SET api_key = ?, theme = ? WHERE user_id = ?", (api_key, theme, user_id))
        conn.commit()
        conn.close()
        return True, "Settings saved!", theme
    except Exception as e:
        return False, f"Error: {str(e)}", "light"

def get_dashboard_stats(user_id):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(DISTINCT topic) FROM learning_history WHERE user_id = ?", (user_id,))
        topics_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM learning_history WHERE user_id = ? AND activity_type = 'quiz'", (user_id,))
        quiz_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT quiz_score FROM learning_history WHERE user_id = ? AND activity_type = 'quiz'", (user_id,))
        scores = cursor.fetchall()
        
        avg_score = 0
        if scores:
            total_correct = 0
            total_questions = 0
            for score, in scores:
                if score:
                    parts = score.split('/')
                    if len(parts) == 2:
                        total_correct += int(parts[0])
                        total_questions += int(parts[1])
            avg_score = (total_correct / total_questions * 100) if total_questions > 0 else 0
        
        cursor.execute("SELECT DISTINCT topic FROM learning_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT 5", (user_id,))
        recent_topics = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(DISTINCT DATE(timestamp)) FROM learning_history WHERE user_id = ? AND timestamp >= datetime('now', '-7 days')", (user_id,))
        streak_days = cursor.fetchone()[0]
        
        cursor.execute("SELECT activity_type, COUNT(*) FROM learning_history WHERE user_id = ? AND timestamp >= datetime('now', '-7 days') GROUP BY activity_type", (user_id,))
        weekly_activity = dict(cursor.fetchall())
        
        conn.close()
        return topics_count, quiz_count, avg_score, recent_topics, streak_days, weekly_activity
    except:
        return 0, 0, 0, [], 0, {}

# ==================== AI FUNCTIONS ====================
def get_ai_response(messages, api_key, temperature=0.7):
    try:
        client = Groq(api_key=api_key)
        chat_completion = client.chat.completions.create(
            messages=messages,
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            max_tokens=2048,
        )
        return chat_completion.choices[0].message.content
    except Exception as e:
        error_str = str(e)
        
        # Handle rate limit errors
        if "rate_limit_exceeded" in error_str or "429" in error_str:
            return """⚠️ **Rate Limit Reached**

You've used up your daily token limit with Groq.

**Solutions:**
1. ⏰ Wait for the limit to reset (check error message for time)
2. 🔄 Try using a different Groq API key
3. ⬆️ Upgrade your Groq account at: https://console.groq.com/settings/billing

**Tip:** The free tier has a daily limit. Consider upgrading for unlimited access!"""
        
        # Handle invalid API key
        elif "invalid" in error_str.lower() or "api" in error_str.lower():
            return """⚠️ **Invalid API Key**

Your Groq API key appears to be invalid.

**How to fix:**
1. Go to: https://console.groq.com/keys
2. Create a new API key
3. Copy it to Settings ⚙️ in this app

**Need an account?** Sign up at: https://console.groq.com"""
        
        # Handle other errors
        else:
            return f"""⚠️ **Error Occurred**

{error_str}

**Troubleshooting:**
- Check your API key in Settings ⚙️
- Verify your internet connection
- Try again in a few moments

**Need help?** Visit: https://console.groq.com/docs"""

def explain_topic(topic, user_id, conv_history):
    if user_id is None:
        return "⚠️ Please sign in first!", "", "", conv_history
    
    api_key, _ = get_user_settings(user_id)
    if not api_key:
        return "⚠️ Set your Groq API key in Settings!", "", "", conv_history
    
    system_prompt = {"role": "system", "content": "You are an expert AI tutor. Provide clear explanations."}
    user_prompt = {"role": "user", "content": f"Explain: {topic}\n\nProvide a comprehensive explanation."}
    
    conv_history = [system_prompt, user_prompt]
    explanation = get_ai_response(conv_history, api_key)
    conv_history.append({"role": "assistant", "content": explanation})
    
    save_to_history(user_id, topic, "explanation", explanation)
    return explanation, "", "", conv_history

def generate_examples(topic, user_id, conv_history):
    if user_id is None:
        return "⚠️ Please sign in!", conv_history
    
    api_key, _ = get_user_settings(user_id)
    if not api_key or not conv_history:
        return "⚠️ Explain a topic first!", conv_history
    
    user_prompt = {"role": "user", "content": f"Provide 3-5 real-world examples of {topic}."}
    conv_history.append(user_prompt)
    examples = get_ai_response(conv_history, api_key)
    conv_history.append({"role": "assistant", "content": examples})
    
    save_to_history(user_id, topic, "examples", examples)
    return examples, conv_history

def generate_quiz(topic, difficulty, user_id, conv_history):
    if user_id is None:
        return "⚠️ Sign in first!", gr.update(visible=False), gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False), None, 0
    
    api_key, _ = get_user_settings(user_id)
    if not api_key or not conv_history:
        return "⚠️ Set API key and explain topic first!", gr.update(visible=False), gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False), None, 0
    
    user_prompt = {
        "role": "user",
        "content": f"""Create 5 {difficulty} multiple-choice questions about {topic}.
Return ONLY JSON array:
[{{"question": "Q1?", "options": ["A", "B", "C", "D"], "correct_answer": 0, "explanation": "Why"}}]
Exactly 5 questions."""
    }
    
    conv_history.append(user_prompt)
    quiz_response = get_ai_response(conv_history, api_key, 0.8)
    
    try:
        cleaned = quiz_response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        quiz = json.loads(cleaned.strip())
        
        if not isinstance(quiz, list) or len(quiz) == 0:
            return "⚠️ Invalid quiz. Try again.", gr.update(visible=False), gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False), None, 0
        
        display = f"### 📝 Question 1 of {len(quiz)}\n\n**{quiz[0]['question']}**"
        quiz_state = {"questions": quiz, "score": {"correct": 0, "total": 0}, "current_index": 0}
        
        return display, gr.update(visible=True, choices=quiz[0]['options'], value=None), gr.update(visible=True), "", gr.update(visible=False), gr.update(visible=False), quiz_state, 0
    except:
        return "⚠️ Error parsing quiz.", gr.update(visible=False), gr.update(visible=False), "", gr.update(visible=False), gr.update(visible=False), None, 0

def submit_answer(selected_option, topic, user_id, quiz_state):
    if quiz_state is None or "questions" not in quiz_state:
        return "⚠️ No active quiz!", "", gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), quiz_state, 0
    
    if selected_option is None:
        return "⚠️ Select an answer!", "", gr.update(), gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), quiz_state, quiz_state.get("current_index", 0)
    
    quiz = quiz_state["questions"]
    idx = quiz_state.get("current_index", 0)
    
    quiz_state["score"]["total"] += 1
    selected_idx = quiz[idx]['options'].index(selected_option)
    
    if selected_idx == quiz[idx]['correct_answer']:
        quiz_state["score"]["correct"] += 1
        result = f"### ✅ Correct!\n\n{quiz[idx]['explanation']}"
    else:
        correct = quiz[idx]['options'][quiz[idx]['correct_answer']]
        result = f"### ❌ Incorrect\n\n**Correct:** {correct}\n\n{quiz[idx]['explanation']}"
    
    score_display = f"**Score: {quiz_state['score']['correct']}/{quiz_state['score']['total']}** ({quiz_state['score']['correct']/quiz_state['score']['total']*100:.1f}%)"
    
    if idx < len(quiz) - 1:
        next_idx = idx + 1
        quiz_state["current_index"] = next_idx
        next_q = f"### 📝 Question {next_idx + 1} of {len(quiz)}\n\n**{quiz[next_idx]['question']}**"
        next_opts = gr.update(choices=quiz[next_idx]['options'], value=None)
        prev_btn = gr.update(visible=True) if next_idx > 0 else gr.update(visible=False)
        next_btn = gr.update(visible=True)
    else:
        final = f"{quiz_state['score']['correct']}/{quiz_state['score']['total']}"
        save_to_history(user_id, topic, "quiz", "", final)
        
        next_q = f"### 🎉 Quiz Complete!\n\n**Final: {final}** ({quiz_state['score']['correct']/quiz_state['score']['total']*100:.1f}%)\n\n"
        if quiz_state['score']['correct'] == quiz_state['score']['total']:
            next_q += "Perfect! 🌟"
        elif quiz_state['score']['correct'] >= quiz_state['score']['total'] * 0.8:
            next_q += "Excellent! 👏"
        else:
            next_q += "Keep practicing! 💪"
        next_opts = gr.update(visible=False)
        prev_btn = gr.update(visible=False)
        next_btn = gr.update(visible=False)
    
    return result, score_display, next_q, next_opts, gr.update(visible=False), prev_btn, next_btn, quiz_state, quiz_state.get("current_index", 0)

def navigate_previous(quiz_state):
    if quiz_state is None or "questions" not in quiz_state:
        return gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), quiz_state, 0
    
    quiz = quiz_state["questions"]
    current_idx = quiz_state.get("current_index", 0)
    
    if current_idx > 0:
        prev_idx = current_idx - 1
        quiz_state["current_index"] = prev_idx
        
        display = f"### 📝 Question {prev_idx + 1} of {len(quiz)}\n\n**{quiz[prev_idx]['question']}**"
        opts = gr.update(choices=quiz[prev_idx]['options'], value=None, visible=True)
        prev_btn = gr.update(visible=True) if prev_idx > 0 else gr.update(visible=False)
        next_btn = gr.update(visible=True)
        
        return display, opts, prev_btn, next_btn, quiz_state, prev_idx
    
    return gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=True), quiz_state, current_idx

def navigate_next(quiz_state):
    if quiz_state is None or "questions" not in quiz_state:
        return gr.update(), gr.update(), gr.update(visible=False), gr.update(visible=False), quiz_state, 0
    
    quiz = quiz_state["questions"]
    current_idx = quiz_state.get("current_index", 0)
    
    if current_idx < len(quiz) - 1:
        next_idx = current_idx + 1
        quiz_state["current_index"] = next_idx
        
        display = f"### 📝 Question {next_idx + 1} of {len(quiz)}\n\n**{quiz[next_idx]['question']}**"
        opts = gr.update(choices=quiz[next_idx]['options'], value=None, visible=True)
        prev_btn = gr.update(visible=True) if next_idx > 0 else gr.update(visible=False)
        next_btn = gr.update(visible=True) if next_idx < len(quiz) - 1 else gr.update(visible=False)
        
        return display, opts, prev_btn, next_btn, quiz_state, next_idx
    
    return gr.update(), gr.update(), gr.update(visible=True), gr.update(visible=False), quiz_state, current_idx

def generate_summary_with_visuals(topic, summary_type, user_id, conv_history):
    if user_id is None:
        return "⚠️ Sign in first!", "", conv_history
    
    api_key, _ = get_user_settings(user_id)
    if not api_key or not conv_history:
        return "⚠️ Set API key and explain topic first!", "", conv_history
    
    if summary_type == "Bullet Points Summary":
        prompt = f"Create bullet point summary of {topic}:\n- Key Concepts\n- Important Details\n- Quick Facts\n- Takeaways"
    elif summary_type == "Visual Learning Guide":
        prompt = f"Create visual guide for {topic}:\n1. Concept Map\n2. Process Flow\n3. Recommended Videos\n4. Image Resources\n5. Memory Aids"
    else:
        prompt = f"Create overview of {topic}:\n### Executive Summary\n### Core Concepts\n### Key Points\n### Applications"
    
    conv_history.append({"role": "user", "content": prompt})
    summary = get_ai_response(conv_history, api_key)
    conv_history.append({"role": "assistant", "content": summary})
    
    # Only generate visual resources for Visual Learning Guide - but only show buttons, no AI text
    visual_html = ""
    if summary_type == "Visual Learning Guide":
        # Don't call AI for resource text, just create the HTML with buttons
        visual_html = create_visual_html(topic)
    
    save_to_history(user_id, topic, "summary", summary)
    
    return summary, visual_html, conv_history

def create_visual_html(topic):
    topic_url = topic.replace(" ", "+")
    
    return f"""
    <div style='background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); padding: 30px; border-radius: 16px; box-shadow: 0 8px 24px rgba(139, 92, 246, 0.3);'>
        <h3 style='margin-top: 0; color: white; font-size: 1.6em; font-weight: 700; text-align: center; margin-bottom: 25px;'>🔗 Visual Learning Resources</h3>
        
        <div style='display: grid; gap: 14px;'>
            <a href='https://www.youtube.com/results?search_query={topic_url}+tutorial' target='_blank' 
               style='background: #FF0000; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                📹 YouTube Tutorial Videos
            </a>
            <a href='https://www.google.com/search?q={topic_url}+diagram+infographic&tbm=isch' target='_blank' 
               style='background: #4285F4; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                🖼️ Visual Diagrams & Infographics
            </a>
            <a href='https://www.google.com/search?q={topic_url}+flowchart+concept+map&tbm=isch' target='_blank' 
               style='background: #34A853; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                📊 Flowcharts & Concept Maps
            </a>
            <a href='https://www.khanacademy.org/search?search_again=1&page_search_query={topic_url}' target='_blank' 
               style='background: #14BF96; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                🎓 Khan Academy Lessons
            </a>
            <a href='https://en.wikipedia.org/wiki/{topic_url}' target='_blank' 
               style='background: #000000; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                📖 Wikipedia Article
            </a>
            <a href='https://www.coursera.org/search?query={topic_url}' target='_blank' 
               style='background: #0056D2; color: white; padding: 16px 24px; text-decoration: none; border-radius: 12px; text-align: center; font-weight: 600; font-size: 1.08em; transition: all 0.3s; display: block; box-shadow: 0 4px 12px rgba(0,0,0,0.2);'>
                🎯 Coursera Courses
            </a>
        </div>
        
        <div style='margin-top: 22px; padding: 16px; background: rgba(255,255,255,0.15); border-radius: 12px; border: 2px solid rgba(255,255,255,0.3); backdrop-filter: blur(10px);'>
            <p style='margin: 0; font-size: 1em; color: white; text-align: center; font-weight: 500;'>
                💡 <strong>Pro Tip:</strong> Click any link above to explore visual learning materials in a new tab!
            </p>
        </div>
    </div>
    """

# ==================== AUTH FUNCTIONS ====================
def signup_user(username, password, confirm_password, email):
    if not username or not password:
        return "⚠️ Username and password required!"
    if password != confirm_password:
        return "⚠️ Passwords don't match!"
    if len(password) < 6:
        return "⚠️ Password must be 6+ characters!"
    
    success, message = create_user(username, password, email)
    return message

def signin_user(username, password):
    if not username or not password:
        return gr.update(), gr.update(), "⚠️ Enter credentials!", "### Welcome!", None, ""
    
    success, user_id, username = verify_user(username, password)
    
    if success:
        _, theme = get_user_settings(user_id)
        welcome = f"### Welcome back, {username}! 👋"
        return gr.update(visible=False), gr.update(visible=True), "", welcome, user_id, theme
    else:
        return gr.update(), gr.update(), "⚠️ Invalid credentials!", "### Welcome!", None, ""

def signout_user():
    return gr.update(visible=True), gr.update(visible=False), "Signed out!", "### Welcome!", None, "light"

def load_dashboard(user_id, theme):
    if user_id is None:
        return "Sign in to view dashboard."
    
    topics, quizzes, avg_score, recent, streak, weekly = get_dashboard_stats(user_id)
    
    bg = "#1a1d2e" if theme == "dark" else "#fafbff"
    card_bg = "#2a2d3e" if theme == "dark" else "#ffffff"
    text = "#e8eaf6" if theme == "dark" else "#1f2937"
    border = "#3a3f5c" if theme == "dark" else "#e5e7eb"
    recent_bg = "#1f2233" if theme == "dark" else "#f9fafb"
    
    html = f"""
    <div style='padding: 35px; background: {bg}; color: {text}; border-radius: 20px; font-family: "Inter", "Segoe UI", Arial, sans-serif;'>
        <h1 style='text-align: center; font-size: 2.4em; margin-bottom: 12px; background: linear-gradient(135deg, #6366f1, #8b5cf6, #d946ef); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800;'>
            📊 Your Learning Dashboard
        </h1>
        <p style='text-align: center; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-size: 1.1em; margin-bottom: 40px; font-weight: 500;'>Track your progress and celebrate achievements</p>
        
        <div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 24px; margin-bottom: 40px;'>
            <div style='background: {card_bg}; padding: 32px; border-radius: 16px; text-align: center; box-shadow: 0 8px 24px rgba(99, 102, 241, {"0.3" if theme == "dark" else "0.15"}); border: 1px solid {border}; transition: transform 0.3s, box-shadow 0.3s;'>
                <div style='font-size: 3.5em; font-weight: 800; background: linear-gradient(135deg, #6366f1, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;'>{topics}</div>
                <div style='font-size: 1.08em; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-weight: 600;'>📚 Topics Studied</div>
            </div>
            
            <div style='background: {card_bg}; padding: 32px; border-radius: 16px; text-align: center; box-shadow: 0 8px 24px rgba(139, 92, 246, {"0.3" if theme == "dark" else "0.15"}); border: 1px solid {border}; transition: transform 0.3s, box-shadow 0.3s;'>
                <div style='font-size: 3.5em; font-weight: 800; background: linear-gradient(135deg, #8b5cf6, #d946ef); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;'>{quizzes}</div>
                <div style='font-size: 1.08em; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-weight: 600;'>🎯 Quizzes Taken</div>
            </div>
            
            <div style='background: {card_bg}; padding: 32px; border-radius: 16px; text-align: center; box-shadow: 0 8px 24px rgba(217, 70, 239, {"0.3" if theme == "dark" else "0.15"}); border: 1px solid {border}; transition: transform 0.3s, box-shadow 0.3s;'>
                <div style='font-size: 3.5em; font-weight: 800; background: linear-gradient(135deg, #d946ef, #ec4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;'>{avg_score:.0f}%</div>
                <div style='font-size: 1.08em; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-weight: 600;'>📈 Average Score</div>
            </div>
            
            <div style='background: {card_bg}; padding: 32px; border-radius: 16px; text-align: center; box-shadow: 0 8px 24px rgba(236, 72, 153, {"0.3" if theme == "dark" else "0.15"}); border: 1px solid {border}; transition: transform 0.3s, box-shadow 0.3s;'>
                <div style='font-size: 3.5em; font-weight: 800; background: linear-gradient(135deg, #ec4899, #f97316); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 10px;'>{streak}</div>
                <div style='font-size: 1.08em; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-weight: 600;'>🔥 Day Streak</div>
            </div>
        </div>
        
        <div style='background: {card_bg}; padding: 28px; border-radius: 16px; box-shadow: 0 8px 24px rgba(99, 102, 241, {"0.2" if theme == "dark" else "0.1"}); border: 1px solid {border};'>
            <h3 style='font-size: 1.5em; margin-top: 0; margin-bottom: 24px; color: {text}; font-weight: 700;'>📚 Recent Topics</h3>
            <div style='display: grid; gap: 14px;'>
"""
    
    if recent:
        gradients = [
            ['#6366f1', '#8b5cf6'],
            ['#8b5cf6', '#d946ef'],
            ['#d946ef', '#ec4899'],
            ['#ec4899', '#f97316'],
            ['#f97316', '#f59e0b']
        ]
        for i, topic in enumerate(recent):
            g = gradients[i % len(gradients)]
            html += f"""
                <div style='background: {recent_bg}; padding: 18px 24px; border-radius: 12px; border-left: 5px solid {g[0]}; font-size: 1.08em; font-weight: 600; transition: all 0.3s; box-shadow: 0 2px 8px rgba(0,0,0,{"0.2" if theme == "dark" else "0.05"});'>
                    <span style='background: linear-gradient(135deg, {g[0]}, {g[1]}); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-weight: 800; font-size: 1.1em;'>{i+1}.</span> {topic}
                </div>
"""
    else:
        html += f"<div style='padding: 40px; text-align: center; color: {"#a8b2d1" if theme == "dark" else "#6b7280"}; font-size: 1.1em; font-weight: 500;'>No topics studied yet. Start your learning journey today! 🚀</div>"
    
    html += """
            </div>
        </div>
    </div>
    """
    
    return html

def save_settings(api_key, theme, user_id):
    if user_id is None:
        return "⚠️ Sign in first!", "light"
    
    success, message, saved_theme = update_user_settings(user_id, api_key, theme)
    return f"✅ {message}" if success else f"⚠️ {message}", saved_theme

def load_settings(user_id):
    if user_id is None:
        return "", "light"
    return get_user_settings(user_id)

# ==================== PREMIUM THEME CSS ====================
def get_theme_css(theme):
    if theme == "dark":
        return """
        <style>
        /* Dark Theme - Premium & Pleasant */
        .gradio-container {
            background: linear-gradient(135deg, #1a1d2e 0%, #2d1b3d 100%) !important;
            font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif !important;
        }
        
        #header {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.4);
            border: 1px solid rgba(255,255,255,0.1);
            position: relative;
            overflow: hidden;
        }
        
        #header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.05) 100%);
            pointer-events: none;
        }
        
        #header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 0.3em;
            letter-spacing: -0.8px;
            position: relative;
            color: white !important;
        }
        
        #header h3 {
            font-size: 1.15em;
            font-weight: 400;
            opacity: 0.95;
            position: relative;
            color: white !important;
        }
        
        .auth-container {
            background: linear-gradient(135deg, #2a2d3e 0%, #1f2233 100%) !important;
            color: #e8eaf6 !important;
            padding: 2.5rem;
            border-radius: 18px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5);
            border: 1px solid rgba(139, 92, 246, 0.2);
        }
        
        .gr-button {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 14px 28px !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4) !important;
            position: relative;
            overflow: hidden;
        }
        
        .gr-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.1) 0%, transparent 100%);
            opacity: 0;
            transition: opacity 0.4s ease;
        }
        
        .gr-button:hover::before {
            opacity: 1;
        }
        
        .gr-button:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 10px 30px rgba(139, 92, 246, 0.6) !important;
        }
        
        .gr-button:active {
            transform: translateY(-1px) scale(0.98);
        }
        
        .gr-button-secondary {
            background: linear-gradient(135deg, #4a5568 0%, #2d3748 100%) !important;
            box-shadow: 0 4px 15px rgba(74, 85, 104, 0.4) !important;
        }
        
        .gr-button-secondary:hover {
            box-shadow: 0 8px 25px rgba(74, 85, 104, 0.6) !important;
        }
        
        #output-explanation, #output-examples, #quiz-question, #output-summary, #quiz-result {
            background: linear-gradient(135deg, #2a2d3e 0%, #252838 100%) !important;
            border-left: 5px solid #8b5cf6 !important;
            color: #e8eaf6 !important;
            padding: 24px !important;
            border-radius: 14px !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
            line-height: 1.8 !important;
            margin: 18px 0 !important;
            border: 1px solid rgba(139, 92, 246, 0.2);
            border-left: 5px solid #8b5cf6 !important;
        }
        
        #output-explanation *, #output-examples *, #quiz-question *, #output-summary *, #quiz-result * {
            color: #e8eaf6 !important;
        }
        
        #output-explanation h1, #output-examples h1, #quiz-question h1, #output-summary h1, #quiz-result h1,
        #output-explanation h2, #output-examples h2, #quiz-question h2, #output-summary h2, #quiz-result h2,
        #output-explanation h3, #output-examples h3, #quiz-question h3, #output-summary h3, #quiz-result h3 {
            color: #c4b5fd !important;
        }
        
        #output-explanation strong, #output-examples strong, #quiz-question strong, #output-summary strong, #quiz-result strong {
            color: #ffffff !important;
        }
        
        /* Error message styling */
        #output-explanation:has(> :first-child:contains("⚠️")),
        #output-examples:has(> :first-child:contains("⚠️")) {
            background: linear-gradient(135deg, #3d2a2e 0%, #2e2535 100%) !important;
            border-left: 5px solid #ef4444 !important;
            border-color: rgba(239, 68, 68, 0.3) !important;
        }
        
        label, .gr-box label {
            color: #e8eaf6 !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            margin-bottom: 10px !important;
        }
        
        input, textarea, select {
            background: #1f2233 !important;
            color: #e8eaf6 !important;
            border: 2px solid #3a3f5c !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            font-size: 1.02em !important;
            transition: all 0.3s ease !important;
        }
        
        input:focus, textarea:focus, select:focus {
            border-color: #8b5cf6 !important;
            box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.25) !important;
            outline: none !important;
            background: #252838 !important;
        }
        
        .gr-form {
            background: linear-gradient(135deg, #2a2d3e 0%, #252838 100%) !important;
            border-radius: 14px !important;
            padding: 24px !important;
            border: 1px solid rgba(139, 92, 246, 0.2) !important;
        }
        
        .gr-panel {
            background: linear-gradient(135deg, #2a2d3e 0%, #252838 100%) !important;
            border-radius: 14px !important;
            border: 1px solid rgba(139, 92, 246, 0.2) !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.4) !important;
        }
        
        .tabs button {
            color: #a8b2d1 !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            padding: 14px 24px !important;
            border-radius: 12px 12px 0 0 !important;
            transition: all 0.3s ease !important;
            background: transparent !important;
        }
        
        .tabs button:hover {
            background: rgba(139, 92, 246, 0.1) !important;
            color: #c4b5fd !important;
        }
        
        .tabs button.selected {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
            color: white !important;
        }
        
        .gr-radio label {
            background: #1f2233 !important;
            border: 2px solid #3a3f5c !important;
            border-radius: 12px !important;
            padding: 14px 20px !important;
            margin: 8px 0 !important;
            transition: all 0.3s ease !important;
            cursor: pointer;
            color: #e8eaf6 !important;
        }
        
        .gr-radio label:hover {
            border-color: #8b5cf6 !important;
            background: #252838 !important;
            transform: translateX(4px);
        }
        
        /* Markdown text visibility */
        .markdown-text, .prose {
            color: #e8eaf6 !important;
        }
        
        p, li, span, div {
            color: inherit;
        }
        </style>
        """
    else:
        return """
        <style>
        /* Light Theme - Premium & Pleasant */
        .gradio-container {
            background: linear-gradient(135deg, #fafbff 0%, #f0f4ff 100%) !important;
            font-family: 'Inter', 'Segoe UI', 'Arial', sans-serif !important;
        }
        
        #header {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%);
            color: white;
            padding: 3rem 2rem;
            border-radius: 20px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 10px 40px rgba(139, 92, 246, 0.3);
            position: relative;
            overflow: hidden;
        }
        
        #header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, transparent 0%, rgba(255,255,255,0.1) 100%);
            pointer-events: none;
        }
        
        #header h1 {
            font-size: 2.5em;
            font-weight: 700;
            margin-bottom: 0.3em;
            letter-spacing: -0.8px;
            position: relative;
        }
        
        #header h3 {
            font-size: 1.15em;
            font-weight: 400;
            opacity: 0.95;
            position: relative;
        }
        
        .auth-container {
            background: white !important;
            padding: 2.5rem;
            border-radius: 18px;
            box-shadow: 0 10px 40px rgba(99, 102, 241, 0.15);
            border: 1px solid #e5e7eb;
        }
        
        .gr-button {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 12px !important;
            padding: 14px 28px !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.35) !important;
            position: relative;
            overflow: hidden;
        }
        
        .gr-button::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.2) 0%, transparent 100%);
            opacity: 0;
            transition: opacity 0.4s ease;
        }
        
        .gr-button:hover::before {
            opacity: 1;
        }
        
        .gr-button:hover {
            transform: translateY(-3px) scale(1.02);
            box-shadow: 0 10px 30px rgba(139, 92, 246, 0.5) !important;
        }
        
        .gr-button:active {
            transform: translateY(-1px) scale(0.98);
        }
        
        .gr-button-secondary {
            background: linear-gradient(135deg, #6b7280 0%, #4b5563 100%) !important;
            box-shadow: 0 4px 15px rgba(107, 114, 128, 0.3) !important;
        }
        
        .gr-button-secondary:hover {
            box-shadow: 0 8px 25px rgba(107, 114, 128, 0.4) !important;
        }
        
        #output-explanation, #output-examples, #quiz-question, #output-summary, #quiz-result {
            background: white !important;
            border-left: 5px solid #8b5cf6 !important;
            color: #1f2937 !important;
            padding: 24px !important;
            border-radius: 14px !important;
            box-shadow: 0 6px 20px rgba(139, 92, 246, 0.12) !important;
            line-height: 1.8 !important;
            margin: 18px 0 !important;
            border: 1px solid #e5e7eb;
            border-left: 5px solid #8b5cf6 !important;
        }
        
        /* Error message styling */
        #output-explanation:has(> :first-child:contains("⚠️")),
        #output-examples:has(> :first-child:contains("⚠️")) {
            background: #fef2f2 !important;
            border-left: 5px solid #ef4444 !important;
            border-color: #fecaca !important;
        }
        
        label, .gr-box label {
            color: #1f2937 !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            margin-bottom: 10px !important;
        }
        
        input, textarea, select {
            background: #ffffff !important;
            color: #1f2937 !important;
            border: 2px solid #d1d5db !important;
            border-radius: 12px !important;
            padding: 14px 18px !important;
            font-size: 1.02em !important;
            transition: all 0.3s ease !important;
        }
        
        input:focus, textarea:focus, select:focus {
            border-color: #8b5cf6 !important;
            box-shadow: 0 0 0 4px rgba(139, 92, 246, 0.15) !important;
            outline: none !important;
            background: #fafbff !important;
        }
        
        .gr-form {
            background: white !important;
            border-radius: 14px !important;
            padding: 24px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.06) !important;
        }
        
        .gr-panel {
            background: white !important;
            border-radius: 14px !important;
            border: 1px solid #e5e7eb !important;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08) !important;
        }
        
        .tabs button {
            color: #6b7280 !important;
            font-weight: 600 !important;
            font-size: 1.05em !important;
            padding: 14px 24px !important;
            border-radius: 12px 12px 0 0 !important;
            transition: all 0.3s ease !important;
            background: transparent !important;
        }
        
        .tabs button:hover {
            background: rgba(139, 92, 246, 0.08) !important;
            color: #8b5cf6 !important;
        }
        
        .tabs button.selected {
            background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
            color: white !important;
        }
        
        .gr-radio label {
            background: #f9fafb !important;
            border: 2px solid #d1d5db !important;
            border-radius: 12px !important;
            padding: 14px 20px !important;
            margin: 8px 0 !important;
            transition: all 0.3s ease !important;
            cursor: pointer;
        }
        
        .gr-radio label:hover {
            border-color: #8b5cf6 !important;
            background: white !important;
            transform: translateX(4px);
            box-shadow: 0 4px 12px rgba(139, 92, 246, 0.15) !important;
        }
        
        h1, h2, h3, h4, h5, h6 {
            color: #1f2937 !important;
        }
        </style>
        """

# ==================== GRADIO APP ====================
init_database()

with gr.Blocks(theme=gr.themes.Soft(), title="AI Tutor") as app:
    
    user_id_state = gr.State(None)
    conv_history_state = gr.State([])
    quiz_state_var = gr.State(None)
    theme_state = gr.State("light")
    
    theme_css = gr.HTML(get_theme_css("light"))
    
    with gr.Column(elem_id="header"):
        gr.Markdown("# 🎓LEARNSPHERE\n### Your Personal Learning Companion • Smart Features")
    
    with gr.Column(visible=True, elem_classes="auth-container") as auth_section:
        gr.Markdown("## 🔐 Sign In or Sign Up")
        
        with gr.Tab("Sign In"):
            signin_username = gr.Textbox(label="Username", placeholder="Enter your username")
            signin_password = gr.Textbox(label="Password", type="password", placeholder="Enter your password")
            signin_btn = gr.Button("🚀 Sign In", variant="primary")
            signin_message = gr.Markdown()
        
        with gr.Tab("Sign Up"):
            signup_username = gr.Textbox(label="Username", placeholder="Choose a username")
            signup_email = gr.Textbox(label="Email (Optional)", placeholder="your.email@example.com")
            signup_password = gr.Textbox(label="Password", type="password", placeholder="Create a password (min 6 characters)")
            signup_confirm = gr.Textbox(label="Confirm Password", type="password", placeholder="Re-enter your password")
            signup_btn = gr.Button("✨ Create Account", variant="primary")
            signup_message = gr.Markdown()
    
    with gr.Column(visible=False) as main_section:
        
        with gr.Row():
            user_display = gr.Markdown()
            signout_btn = gr.Button("🚪 Sign Out", size="sm")
        
        with gr.Tabs():
            
            with gr.Tab("📊 Dashboard"):
                dashboard_content = gr.HTML()
                refresh_dashboard = gr.Button("🔄 Refresh Dashboard", variant="secondary")
            
            with gr.Tab("📚 Learn"):
                topic_input = gr.Textbox(label="What would you like to learn today?", placeholder="e.g., Machine Learning, Photosynthesis, Spanish Grammar...")
                explain_btn = gr.Button("🚀 Start Learning", variant="primary", size="lg")
                output_explanation = gr.Markdown(elem_id="output-explanation")
                examples_btn = gr.Button("💡 Show Real-World Examples", variant="secondary", size="lg")
                output_examples = gr.Markdown(elem_id="output-examples")
            
            with gr.Tab("🎯 Quiz"):
                quiz_difficulty = gr.Radio(choices=["Easy", "Medium", "Hard"], value="Medium", label="Select Difficulty Level")
                generate_quiz_btn = gr.Button("📝 Generate Quiz (5 Questions)", variant="primary", size="lg")
                quiz_question = gr.Markdown(elem_id="quiz-question")
                quiz_options = gr.Radio(label="Choose Your Answer", visible=False)
                
                with gr.Row():
                    prev_question_btn = gr.Button("⬅️ Previous", visible=False, size="sm")
                    submit_answer_btn = gr.Button("✓ Submit Answer", visible=False, variant="primary")
                    next_question_btn = gr.Button("Next ➡️", visible=False, size="sm")
                
                quiz_result = gr.Markdown(elem_id="quiz-result")
                quiz_score_display = gr.Markdown()
                current_question_idx = gr.State(0)
            
            with gr.Tab("📊 Summarize & Visualize"):
                gr.Markdown("### 📊 Get Summaries with Visual Learning Resources")
                summary_type = gr.Radio(
                    choices=["Bullet Points Summary", "Visual Learning Guide", "Comprehensive Overview"],
                    value="Visual Learning Guide",
                    label="Choose Summary Format"
                )
                generate_summary_btn = gr.Button("📋 Generate Summary", variant="primary", size="lg")
                with gr.Row():
                    with gr.Column():
                        output_summary = gr.Markdown(elem_id="output-summary")
                    with gr.Column():
                        output_visual_resources = gr.HTML()
            
            with gr.Tab("📜 History"):
                history_content = gr.Markdown()
                refresh_history = gr.Button("🔄 Refresh History", variant="secondary")
            
            with gr.Tab("⚙️ Settings"):
                gr.Markdown("### ⚙️ Customize Your Experience")
                settings_api_key = gr.Textbox(label="🔑 Groq API Key", type="password", placeholder="Enter your Groq API key")
                settings_theme = gr.Radio(choices=["light", "dark"], value="light", label="🎨 Choose Theme")
                save_settings_btn = gr.Button("💾 Save Settings", variant="primary", size="lg")
                settings_message = gr.Markdown()
    
    # Event Handlers
    signup_btn.click(signup_user, [signup_username, signup_password, signup_confirm, signup_email], signup_message)
    
    signin_btn.click(signin_user, [signin_username, signin_password], [auth_section, main_section, signin_message, user_display, user_id_state, theme_state]
    ).then(load_dashboard, [user_id_state, theme_state], dashboard_content
    ).then(lambda theme: gr.HTML(get_theme_css(theme)), theme_state, theme_css)
    
    signout_btn.click(signout_user, None, [auth_section, main_section, signin_message, user_display, user_id_state, theme_state]
    ).then(lambda: gr.HTML(get_theme_css("light")), None, theme_css)
    
    explain_btn.click(explain_topic, [topic_input, user_id_state, conv_history_state], [output_explanation, output_examples, quiz_question, conv_history_state])
    examples_btn.click(generate_examples, [topic_input, user_id_state, conv_history_state], [output_examples, conv_history_state])
    
    generate_quiz_btn.click(generate_quiz, [topic_input, quiz_difficulty, user_id_state, conv_history_state], [quiz_question, quiz_options, submit_answer_btn, quiz_result, prev_question_btn, next_question_btn, quiz_state_var, current_question_idx])
    
    submit_answer_btn.click(submit_answer, [quiz_options, topic_input, user_id_state, quiz_state_var], [quiz_result, quiz_score_display, quiz_question, quiz_options, submit_answer_btn, prev_question_btn, next_question_btn, quiz_state_var, current_question_idx])
    
    prev_question_btn.click(navigate_previous, [quiz_state_var], [quiz_question, quiz_options, prev_question_btn, next_question_btn, quiz_state_var, current_question_idx])
    
    next_question_btn.click(navigate_next, [quiz_state_var], [quiz_question, quiz_options, prev_question_btn, next_question_btn, quiz_state_var, current_question_idx])
    
    generate_summary_btn.click(generate_summary_with_visuals, [topic_input, summary_type, user_id_state, conv_history_state], [output_summary, output_visual_resources, conv_history_state])
    
    refresh_dashboard.click(load_dashboard, [user_id_state, theme_state], dashboard_content)
    refresh_history.click(get_user_history, user_id_state, history_content)
    
    save_settings_btn.click(save_settings, [settings_api_key, settings_theme, user_id_state], [settings_message, theme_state]
    ).then(load_settings, user_id_state, [settings_api_key, settings_theme]
    ).then(lambda theme: gr.HTML(get_theme_css(theme)), theme_state, theme_css
    ).then(load_dashboard, [user_id_state, theme_state], dashboard_content)

if __name__ == "__main__":
    print("=" * 70)
    print("🚀 AI Tutor Platform v2.0 - PREMIUM EDITION")
    print("=" * 70)
    print("✅ Premium pleasant design with gradient buttons")
    print("✅ Visual resources only in Visual Learning Guide")
    print("✅ Professional light & dark themes")
    print("✅ Smooth animations and interactions")
    print("🌐 http://127.0.0.1:7860")
    print("=" * 70)
    app.launch(share=False, server_name="127.0.0.1", server_port=7860)