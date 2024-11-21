from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import psycopg2
from psycopg2.extras import RealDictCursor, Json
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your_secret_key' 

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Database connection
def connect_db():
    try:
        conn = psycopg2.connect(
            dbname="Website_Book",
            user="postgres",
            password="1234",
            host="localhost",
            port='5432'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to database:", e)
        return None

# Create tables if not exists
def create_tables():
    try:
        conn = connect_db()
        cur = conn.cursor()
        
        # Create users table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL
            );
        """)
        
        # Create books table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id SERIAL PRIMARY KEY,
                title VARCHAR(255) NOT NULL,
                author VARCHAR(255) NOT NULL,
                year INTEGER NOT NULL,
                genre VARCHAR(100) NOT NULL
            );
        """)

        # Create history table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                action_type VARCHAR(50) NOT NULL,
                book_title VARCHAR(255) NOT NULL,
                old_data JSONB,
                new_data JSONB,
                action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Error creating tables:", e)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Check if username exists and password is correct
        cur.execute("SELECT * FROM users WHERE username = %s AND password = %s", 
                   (username, password))
        user = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = connect_db()
        cur = conn.cursor()
        
        try:
            cur.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, password)
            )
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except psycopg2.Error as e:
            conn.rollback()
            flash('Registration failed. Username or email may already exist.', 'error')
        finally:
            cur.close()
            conn.close()
            
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("SELECT * FROM books ORDER BY id")
    books = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', books=books)

@app.route('/add_book', methods=['POST'])
@login_required
def add_book():
    try:
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        genre = request.form['genre']
        
        if not all([title, author, year, genre]):
            return jsonify({"error": "All fields are required"}), 400
        
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Add new book
        cur.execute(
            "INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s) RETURNING *",
            (title, author, year, genre)
        )
        new_book = cur.fetchone()
        
        # Add to history
        cur.execute("""
            INSERT INTO history (user_id, action_type, book_title, new_data)
            VALUES (%s, %s, %s, %s)
        """, (
            session['user_id'],
            'ADD',
            title,
            Json(new_book)
        ))
        
        conn.commit()
        cur.close()
        conn.close()
        
        flash('Book added successfully!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error adding book: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/update_book/<int:id>', methods=['POST'])
@login_required
def update_book(id):
    try:
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get old book data
        cur.execute("SELECT * FROM books WHERE id = %s", (id,))
        old_book = cur.fetchone()

        # Update book
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        genre = request.form['genre']
        
        new_data = {
            'title': title,
            'author': author,
            'year': year,
            'genre': genre
        }

        cur.execute(
            "UPDATE books SET title=%s, author=%s, year=%s, genre=%s WHERE id=%s",
            (title, author, year, genre, id)
        )

        # Add to history
        cur.execute("""
            INSERT INTO history (user_id, action_type, book_title, old_data, new_data)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            session['user_id'],
            'UPDATE',
            old_book['title'],
            Json(dict(old_book)),
            Json(new_data)
        ))

        conn.commit()
        cur.close()
        conn.close()
        
        flash('Book updated successfully!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error updating book: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/delete_book/<int:id>', methods=['POST'])
@login_required
def delete_book(id):
    try:
        conn = connect_db()
        cur = conn.cursor(cursor_factory=RealDictCursor)

        # Get book data before deletion
        cur.execute("SELECT * FROM books WHERE id = %s", (id,))
        book = cur.fetchone()

        # Delete book
        cur.execute("DELETE FROM books WHERE id=%s", (id,))

        # Add to history
        cur.execute("""
            INSERT INTO history (user_id, action_type, book_title, old_data)
            VALUES (%s, %s, %s, %s)
        """, (
            session['user_id'],
            'DELETE',
            book['title'],
            Json(dict(book))
        ))

        conn.commit()
        cur.close()
        conn.close()
        
        flash('Book deleted successfully!', 'success')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Error deleting book: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/history')
@login_required
def history():
    conn = connect_db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT h.*, u.username 
        FROM history h 
        JOIN users u ON h.user_id = u.id 
        ORDER BY h.action_date DESC
    """)
    history = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('history.html', history=history)

if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
