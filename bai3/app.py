from flask import Flask, render_template, request, jsonify, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Cấu hình database
DB_CONFIG = {
    "dbname": "227480201IS003",
    "user": "postgres",
    "password": "1234",
    "host": "localhost",
    "port": "5432"
}

def connect_db():
    """Thiết lập kết nối database"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        print(f"Lỗi kết nối database:", e)
        return None

def create_table():
    """Tạo bảng books nếu chưa tồn tại"""
    try:
        conn = connect_db()
        if conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS books (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(255) NOT NULL,
                        author VARCHAR(255) NOT NULL,
                        year INTEGER NOT NULL,
                        genre VARCHAR(100) NOT NULL
                    );
                """)
                conn.commit()
            conn.close()
    except Exception as e:
        print("Lỗi khi tạo bảng:", e)

@app.route('/')
def index():
    """Hiển thị trang chủ với danh sách sách"""
    try:
        conn = connect_db()
        if conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM books ORDER BY id")
                books = cur.fetchall()
            conn.close()
            return render_template('index.html', books=books)
        return "Lỗi kết nối database", 500
    except Exception as e:
        return f"Lỗi: {str(e)}", 500

@app.route('/add_book', methods=['POST'])
def add_book():
    """Thêm sách mới"""
    try:
        # Lấy dữ liệu từ form
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        genre = request.form['genre']

        # Kiểm tra dữ liệu
        if not all([title, author, year, genre]):
            return jsonify({"error": "Vui lòng điền đầy đủ thông tin"}), 400

        # Thêm vào database
        conn = connect_db()
        if conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO books (title, author, year, genre) VALUES (%s, %s, %s, %s)",
                    (title, author, year, genre)
                )
                conn.commit()
            conn.close()
            return redirect(url_for('index'))
        return jsonify({"error": "Lỗi kết nối database"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_book/<int:id>', methods=['POST'])
def update_book(id):
    """Cập nhật thông tin sách"""
    try:
        # Lấy dữ liệu từ form
        title = request.form['title']
        author = request.form['author']
        year = request.form['year']
        genre = request.form['genre']

        conn = connect_db()
        if conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE books SET title=%s, author=%s, year=%s, genre=%s WHERE id=%s",
                    (title, author, year, genre, id)
                )
                conn.commit()
            conn.close()
            return redirect(url_for('index'))
        return jsonify({"error": "Lỗi kết nối database"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/delete_book/<int:id>', methods=['POST'])
def delete_book(id):
    """Xóa sách"""
    try:
        conn = connect_db()
        if conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM books WHERE id=%s", (id,))
                conn.commit()
            conn.close()
            return redirect(url_for('index'))
        return jsonify({"error": "Lỗi kết nối database"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    create_table()
    app.run(debug=True)