from flask import Flask, send_from_directory, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
import os
import ssl
import pg8000.dbapi
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables (local dev only; Vercel injects them natively)
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PARENT_DIR = os.path.dirname(BASE_DIR)

app = Flask(__name__)
# Secret key for session cookie encryption
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'default_fallback_secret_key_129837128937')

# Force secure cookies in production (HTTPS)
IS_PRODUCTION = os.environ.get('VERCEL_ENV') in ('production', 'preview')
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


def get_db_connection():
    database_url = os.environ.get('DATABASE_URL', '')
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is not set!")

    # Correct legacy postgres:// prefix
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)

    # Parse PostgreSQL connection URI
    result = urlparse(database_url)
    username = result.username
    password = result.password
    database = result.path[1:]  # Remove leading slash
    hostname = result.hostname
    port = result.port or 5432

    # Supabase requires SSL — create a permissive SSL context
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE

    conn = pg8000.dbapi.connect(
        user=username,
        password=password,
        host=hostname,
        port=port,
        database=database,
        ssl_context=ssl_ctx
    )
    return conn


# Helper functions to convert DB-API results to dicts
def fetchall_dict(cur):
    desc = cur.description
    if not desc:
        return []
    columns = [col[0] for col in desc]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetchone_dict(cur):
    desc = cur.description
    if not desc:
        return None
    columns = [col[0] for col in desc]
    row = cur.fetchone()
    if row:
        return dict(zip(columns, row))
    return None


def get_initials(name):
    """Return two-letter initials from a full name."""
    words = name.strip().split()
    if len(words) >= 2:
        return (words[0][0] + words[1][0]).upper()
    elif len(words) == 1 and len(words[0]) >= 2:
        return (words[0][0] + words[0][1]).upper()
    elif len(words) == 1:
        return words[0][0].upper()
    return "??"


# Database Setup — called lazily on first request so env vars are available
def init_db():
    database_url = os.environ.get('DATABASE_URL', '')
    if not database_url:
        print("Warning: DATABASE_URL is not set. Skipping database initialization.")
        return

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Create users table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    handle TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );
            """)

            # Create votes table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS votes (
                    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                    problem_key TEXT NOT NULL,
                    vote_value INTEGER NOT NULL,
                    PRIMARY KEY (user_id, problem_key)
                );
            """)

            # Seed default admin account if it doesn't exist
            cur.execute("SELECT id FROM users WHERE handle = 'admin';")
            if not cur.fetchone():
                admin_pw = os.environ.get('ADMIN_PASSWORD', 'admin123')
                hashed_pw = generate_password_hash(admin_pw)
                cur.execute(
                    "INSERT INTO users (name, handle, password) VALUES (%s, %s, %s);",
                    ('Admin User', 'admin', hashed_pw)
                )
                print("Admin user seeded successfully.")

            conn.commit()
            print("Database initialized successfully.")
    except Exception as e:
        print(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


# Initialize Database immediately (works for both local and Vercel cold start)
init_db()


# Helper function to serve static HTML pages
def serve_html(filename):
    filepath = os.path.join(PARENT_DIR, filename)
    if os.path.exists(filepath):
        return send_from_directory(PARENT_DIR, filename)
    return send_from_directory(BASE_DIR, filename)


# ─── HTML Page Routes ──────────────────────────────────────────────────────────

@app.route('/')
def index():
    return serve_html('final.html')


@app.route('/legacy')
def legacy():
    return serve_html('problem_blueprint_2898.html')


@app.route('/interactive')
def interactive():
    return serve_html('problem_blueprint_2898_inter.html')


@app.route('/interactive_2')
@app.route('/interactive2')
@app.route('/inter_2')
def interactive_2():
    return serve_html('problem_blueprint_2898_inter_2.html')


@app.route('/admin')
def admin():
    return serve_html('admin.html')


# ─── API Routes ────────────────────────────────────────────────────────────────

@app.route('/api/init', methods=['GET'])
def api_init():
    user_data = None
    user_votes = {}
    aggregated_scores = {}

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # 1. Fetch current logged-in user if session exists
            if 'user_id' in session:
                cur.execute("SELECT id, name, handle FROM users WHERE id = %s;", (session['user_id'],))
                db_user = fetchone_dict(cur)
                if db_user:
                    user_data = {
                        "name": db_user['name'],
                        "handle": db_user['handle'],
                        "initials": get_initials(db_user['name'])
                    }

                    # 2. Fetch this user's individual votes
                    cur.execute("SELECT problem_key, vote_value FROM votes WHERE user_id = %s;", (db_user['id'],))
                    for v in fetchall_dict(cur):
                        user_votes[v['problem_key']] = v['vote_value']

            # 3. Fetch aggregated scores for all problems
            cur.execute("SELECT problem_key, SUM(vote_value) as score FROM votes GROUP BY problem_key;")
            for s in fetchall_dict(cur):
                aggregated_scores[s['problem_key']] = int(s['score'])

    except Exception as e:
        print(f"Error in api_init: {e}")
        # Return gracefully — frontend can handle empty data
    finally:
        if conn:
            conn.close()

    return jsonify({
        "user": user_data,
        "votes": user_votes,
        "scores": aggregated_scores
    })


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json() or {}
    handle = data.get('handle', '').strip().lower()
    password = data.get('password', '')

    if not handle or not password:
        return jsonify({"error": "Handle and password are required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, handle, password FROM users WHERE LOWER(handle) = %s;", (handle,))
            db_user = fetchone_dict(cur)
            if db_user and check_password_hash(db_user['password'], password):
                session['user_id'] = db_user['id']
                return jsonify({
                    "success": True,
                    "user": {
                        "name": db_user['name'],
                        "handle": db_user['handle'],
                        "initials": get_initials(db_user['name'])
                    }
                })
    except Exception as e:
        print(f"Error in api_login: {e}")
        return jsonify({"error": "Server error during login"}), 500
    finally:
        if conn:
            conn.close()

    return jsonify({"error": "Invalid handle or password"}), 401


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.pop('user_id', None)
    return jsonify({"success": True})


@app.route('/api/vote', methods=['POST'])
def api_vote():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    problem_key = data.get('problem_key')
    vote_value = data.get('vote_value')

    if not problem_key or vote_value not in [1, -1, 0]:
        return jsonify({"error": "Invalid vote data"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if vote_value == 0:
                cur.execute(
                    "DELETE FROM votes WHERE user_id = %s AND problem_key = %s;",
                    (session['user_id'], problem_key)
                )
            else:
                cur.execute("""
                    INSERT INTO votes (user_id, problem_key, vote_value)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (user_id, problem_key)
                    DO UPDATE SET vote_value = EXCLUDED.vote_value;
                """, (session['user_id'], problem_key, vote_value))
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_vote: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/users', methods=['GET'])
def api_admin_users():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Verify the current user is admin
            cur.execute("SELECT handle FROM users WHERE id = %s;", (session['user_id'],))
            current_user = fetchone_dict(cur)
            if not current_user or current_user['handle'] != 'admin':
                return jsonify({"error": "Forbidden"}), 403

            cur.execute("SELECT name, handle FROM users ORDER BY name ASC;")
            users_list = fetchall_dict(cur)

            formatted_users = [
                {
                    "name": u['name'],
                    "handle": u['handle'],
                    "initials": get_initials(u['name'])
                }
                for u in users_list
            ]

            return jsonify({"users": formatted_users})
    except Exception as e:
        print(f"Error in api_admin_users: {e}")
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/admin/create_user', methods=['POST'])
def api_admin_create_user():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    name = data.get('name', '').strip()
    handle = data.get('handle', '').strip().lower()
    password = data.get('password', '')

    if not name or not handle or not password:
        return jsonify({"error": "Name, handle, and password are required"}), 400

    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Verify current user is admin
            cur.execute("SELECT handle FROM users WHERE id = %s;", (session['user_id'],))
            current_user = fetchone_dict(cur)
            if not current_user or current_user['handle'] != 'admin':
                return jsonify({"error": "Forbidden"}), 403

            # Check for duplicate handle
            cur.execute("SELECT id FROM users WHERE LOWER(handle) = %s;", (handle,))
            if cur.fetchone():
                return jsonify({"error": "User with this handle already exists"}), 400

            hashed_pw = generate_password_hash(password)
            cur.execute(
                "INSERT INTO users (name, handle, password) VALUES (%s, %s, %s);",
                (name, handle, hashed_pw)
            )
            conn.commit()
            return jsonify({"success": True})
    except Exception as e:
        print(f"Error in api_admin_create_user: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Database error"}), 500
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
