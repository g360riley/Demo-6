from flask import Blueprint, render_template, request, redirect, url_for, flash, g, jsonify
import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

chatbot = Blueprint('chatbot', __name__)

# Available models (updated for current Groq API)
AVAILABLE_MODELS = {
    'llama-3.3-70b-versatile': 'Llama 3.3 70B (Versatile & Powerful)',
    'llama-3.1-8b-instant': 'Llama 3.1 8B (Fast)',
    'mixtral-8x7b-32768': 'Mixtral 8x7B (Balanced)',
    'gemma2-9b-it': 'Gemma 2 9B (Efficient)'
}

@chatbot.route('/', methods=['GET', 'POST'])
def show_chatbot():
    response_text = None
    current_question = None

    if request.method == 'POST':
        user_question = request.form.get('question', '').strip()
        selected_model = request.form.get('model', 'llama-3.1-8b-instant')

        if not user_question:
            flash('Question is required!', 'error')
            return redirect(url_for('chatbot.show_chatbot'))

        current_question = user_question

        try:
            # Get Groq API key
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key or api_key == 'your_groq_api_key_here':
                flash('Groq API key not configured', 'error')
                return redirect(url_for('chatbot.show_chatbot'))

            # Initialize Groq client
            client = Groq(api_key=api_key)

            # Create table if it doesn't exist (enhanced schema)
            cursor = g.db.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chatbot_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    model VARCHAR(50) DEFAULT 'llama-3.1-8b-instant',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Validate model selection
            if selected_model not in AVAILABLE_MODELS:
                selected_model = 'llama-3.1-8b-instant'

            # Call Groq API
            chat_completion = client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful AI assistant. Provide clear, accurate, and concise responses."
                    },
                    {
                        "role": "user",
                        "content": user_question,
                    }
                ],
                model=selected_model,
                temperature=0.7,
                max_tokens=1024
            )

            response_text = chat_completion.choices[0].message.content

            # Save to database
            cursor.execute(
                'INSERT INTO chatbot_history (question, answer, model) VALUES (%s, %s, %s)',
                (user_question, response_text, selected_model)
            )
            g.db.commit()

            flash(f'Question answered successfully using {AVAILABLE_MODELS[selected_model]}!', 'success')
        except Exception as e:
            flash(f'Error getting AI response: {str(e)}', 'error')
            response_text = None

    # Get chat history
    try:
        cursor = g.db.cursor()
        cursor.execute('SELECT * FROM chatbot_history ORDER BY id DESC LIMIT 20')
        chat_history = cursor.fetchall()
    except:
        chat_history = []
        cursor = g.db.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chatbot_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                model VARCHAR(50) DEFAULT 'llama-3.1-8b-instant',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        g.db.commit()

    return render_template('chatbot.html', response=response_text, history=chat_history,
                          models=AVAILABLE_MODELS, current_question=current_question)

@chatbot.route('/delete/<int:chat_id>')
def delete_chat(chat_id):
    """Delete a specific chat message from history"""
    try:
        cursor = g.db.cursor()
        cursor.execute('DELETE FROM chatbot_history WHERE id = %s', (chat_id,))
        g.db.commit()
        flash('Chat message deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting chat message: {str(e)}', 'error')

    return redirect(url_for('chatbot.show_chatbot'))

@chatbot.route('/clear-history')
def clear_history():
    """Clear all chat history"""
    try:
        cursor = g.db.cursor()
        cursor.execute('DELETE FROM chatbot_history')
        g.db.commit()
        flash('Chat history cleared successfully!', 'success')
    except Exception as e:
        flash(f'Error clearing chat history: {str(e)}', 'error')

    return redirect(url_for('chatbot.show_chatbot'))
