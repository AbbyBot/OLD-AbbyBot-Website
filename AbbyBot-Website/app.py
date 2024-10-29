import mysql.connector
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import os
from contextlib import contextmanager
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException


# Load dotenv variables
load_dotenv()

# Start Flask
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Consolidated DB connection function
def get_db_connection(db_type="rei"):
    if db_type == "rei":
        return mysql.connector.connect(
            host=os.getenv("REI_DB_HOST"),
            user=os.getenv("REI_DB_USER"),
            password=os.getenv("REI_DB_PASSWORD"),
            database=os.getenv("REI_DB_NAME")
        )
    elif db_type == "asuka":
        return mysql.connector.connect(
            host=os.getenv("ASUKA_DB_HOST"),
            user=os.getenv("ASUKA_DB_USER"),
            password=os.getenv("ASUKA_DB_PASSWORD"),
            database=os.getenv("ASUKA_DB_NAME")
        )

# Context Manager for both DBs
@contextmanager
def db_connection(db_type="rei"):
    conn = None
    try:
        conn = get_db_connection(db_type)
        yield conn
    finally:
        if conn is not None:
            conn.close()


# Helper function to execute queries
def execute_query(db_type, query, params=None, fetchall=True, commit=False):
    try:
        with db_connection(db_type) as conn:
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute(query, params or ())
                if commit:
                    conn.commit()
                if fetchall:
                    result = cursor.fetchall()
                else:
                    result = cursor.fetchone()
        return result
    
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        raise  # Rethrow the exception so it can be handled by the calling function
    
    except Exception as e:
        print(f"Unexpected Error: {e}")
        raise  # Rethrow any other unexpected exceptions



# Home route
@app.route('/')
def home():
    try:
        server_list = execute_query("rei", "SELECT COUNT(guild_id) as counter FROM server_settings;")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Database connection failed.")
    
    return render_template('home.html', server_list=server_list)

# Overview route
@app.route('/overview')
def overview():
    return render_template('overview.html')

# About her route
@app.route('/about-her')
def abouther():
    return render_template('about-her.html')

# Contribute route
@app.route('/contribute')
def contribute():
    return render_template('contribute.html')

# Commands list route
@app.route('/commands-list')
def commands_list():
    try:
        en_commands_list = execute_query("rei", "SELECT * FROM help WHERE language_id = 1;")
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Database connection failed.")
    
    return render_template('commands-list.html', commands=en_commands_list)

# Wishlist route - handles form submissions
@app.route('/wishlist', methods=['GET', 'POST'])
def wishlist():
    if request.method == 'POST':
        # Get form data
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        discord_username = request.form.get('discord_username', '').strip()
        reason = request.form.get('reason', '').strip()
        how_learned = request.form.get('how_learned', '').strip()

        # Validate required fields
        if not name or not email:
            flash("Name and Email are required!", 'danger')
            return redirect(url_for('wishlist'))

        try:
            # Insert the data into the wishlist database
            execute_query("asuka", """
                INSERT INTO wishlist (name, email, discord_username, reason, how_learned)
                VALUES (%s, %s, %s, %s, %s)
            """, (name, email, discord_username, reason, how_learned), fetchall=False, commit=True)
            
            flash("Your wishlist submission has been received successfully!", 'success')
            return redirect(url_for('home'))

        except mysql.connector.Error as err:
            flash(f"Database Error: {err}", 'danger')
            print(f"Database Error: {err}")

        except Exception as e:
            flash(f"Unexpected Error: {e}", 'danger')
            print(f"Unexpected Error: {e}")

    return render_template('wishlist.html')



# Contact us route
@app.route('/contact-us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        # Get form data
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        message = request.form['message'].strip()

        # Validate required fields
        if not name or not email or not message:
            flash("Name, Email, and Message are required!", 'danger')
            return redirect(url_for('contact_us'))

        try:
            # Insert data into the messages table (Asuka DB)
            execute_query("asuka", """
                INSERT INTO messages (name, email, message)
                VALUES (%s, %s, %s)
            """, (name, email, message), fetchall=False, commit=True)

            flash("Thank you for contacting us! We will get back to you soon.", "success")
            return redirect(url_for('home'))

        except mysql.connector.Error as err:
            flash(f"Database Error: {err}", 'danger')
            print(f"Database Error: {err}")
        
        except Exception as e:
            flash(f"Unexpected Error: {e}", 'danger')
            print(f"Unexpected Error: {e}")

    return render_template('contact-us.html')




@app.route('/thank-you')
def thank_you():
    return render_template('thank-you.html')

@app.route('/wip')
def wip():
    return render_template('work-in-progress.html')

# Terms and conditions route
@app.route('/terms-and-conditions')
def terms_and_conditions():
    return render_template('terms-and-conditions.html')

# Hall of fame route
@app.route('/hall-of-fame')
def hall_of_fame():
    try:
        # Fetch hall of fame data
        hall_of_fame_data = execute_query("asuka", """
            SELECT id, nickname AS name, username as username, user_image AS image_url, custom_nickname 
            FROM contributors
        """)
        users_names_list = execute_query("rei", """
            SELECT up.user_username AS bro_username
            FROM dashboard d
            JOIN user_profile up ON d.user_profile_id = up.id
            WHERE d.guild_id = 1176976421147648061 
            AND d.is_bot = 0;
        """)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Database connection failed.")

    return render_template('hall_of_fame.html', hall_of_fame_data=hall_of_fame_data, users_names_list=users_names_list)


@app.route('/hall-of-fame/contributor/<string:username>')
def person_detail(username):
    try:
        # Inquire for contributor information
        person = execute_query("asuka", """
            SELECT id, nickname AS name, username, user_image AS image_url, commentary, custom_nickname 
            FROM contributors WHERE username = %s
        """, (username,), fetchall=False)
        
        # If the contributor exists, search for their contributions
        if person:
            # Inquiry for related contributions
            contributions = execute_query("asuka", """
                SELECT contribution 
                FROM contributions WHERE contributor_id = %s
            """, (person['id'],))
        else:
            # Render the custom error page for person not found
            return render_template('error.html', message="Person not found.", code=404), 404
    
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Database connection failed.", code=500), 500
    
    # Render the detail page for the person if found
    return render_template('person_detail.html', person=person, contributions=contributions)


# Error handling route for all HTTP errors
@app.errorhandler(Exception)
def handle_error(e):
    code = 500  # Default to internal server error
    message = "An unexpected error occurred."

    # If it's an HTTPException, get the error code and message
    if isinstance(e, HTTPException):
        code = e.code
        message = e.description

    # Custom messages for specific HTTP codes
    if code == 404:
        message = "The page you are looking for does not exist."
    elif code == 403:
        message = "You don't have permission to access this resource."
    elif code == 500:
        message = "Internal server error. Please try again later."
    elif code == 401:
        message = "Unauthorized access. Please log in to continue."

    return render_template('error.html', message=message, code=code), code


# List of allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configure the folder where the images will be saved
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'static/img/contributor')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['ALLOWED_EXTENSIONS'] = ALLOWED_EXTENSIONS



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



class Admin(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash  

    @staticmethod
    def get_admin_by_username(username):
        result = execute_query("asuka", "SELECT * FROM admins WHERE username = %s", (username,), fetchall=False)
        if result:
            return Admin(result['id'], result['username'], result['email'], result['password'])  # use hash

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)  # compare hash with normal password

# login routes

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    result = execute_query("asuka", "SELECT * FROM admins WHERE id = %s", (user_id,), fetchall=False)
    if result:
        return Admin(result['id'], result['username'], result['email'], result['password'])
    return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin = Admin.get_admin_by_username(username)
        if admin:
            if admin.check_password(password):
                login_user(admin)
                flash(f'Logged in as {username}.', 'Success')
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Incorrect password.', 'Error')
        else:
            flash('User not found.', 'Error')
    
    return render_template('login.html')

# logout

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'Success')
    return redirect(url_for('login'))

# dashboard base

@app.route('/admin-dashboard')
@login_required
def admin_dashboard():
    username = current_user.username
    return render_template('admin_dashboard.html', username=username)

# manage all messages

@app.route('/admin-manage_messages')
@login_required
def admin_manage_messages():
    try:
            # Get all messages
            all_messages = execute_query("asuka", """
                SELECT id, name, email, message, created_at FROM messages
            """)
    except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', message="Database connection failed.")
    return render_template('admin_manage_messages.html', messages=all_messages)

# manage message by id

@app.route('/admin-message/<int:message_id>')
@login_required
def view_message_details(message_id):
    try:
        # Get the message details from the database using its ID
        message = execute_query("asuka", """
            SELECT id, name, email, message, created_at FROM messages WHERE id = %s
        """, (message_id,))
        
        if not message:
            return render_template('error.html', message="Message not found.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Database connection failed.")

    return render_template('view_message_details.html', message=message[0])

# manage wishlists

@app.route('/admin-manage_wishlist')
@login_required
def admin_manage_wishlist():
    try:
            # Get all messages
            all_wishlist = execute_query("asuka", """
                SELECT id, name, email, discord_username, reason, how_learned, submitted_at FROM wishlist
            """)
    except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', wishlists="Database connection failed.")
    return render_template('admin_manage_wishlist.html', wishlists=all_wishlist)

# manage wishlist by id

@app.route('/admin-wishlist/<int:wishlist_id>')
@login_required
def view_wishlist_details(wishlist_id):
    try:
        # Get the wishlist details from the database using its ID
        wishlist = execute_query("asuka", """
            SELECT id, name, email, discord_username, reason, how_learned, submitted_at FROM wishlist where id = %s
        """, (wishlist_id,))
        
        if not wishlist:
            return render_template('error.html', wishlist="Message not found.")

    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', wishlist="Database connection failed.")

    return render_template('view_wishlist_details.html', wishlist=wishlist[0])

# manage contributors
@app.route('/admin-manage_contributors')
@login_required
def admin_manage_contributors():
    connection = None
    cursor = None
    try:
        # Get all contributors
        connection = get_db_connection(db_type="asuka")
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, nickname, username, commentary, user_image, custom_nickname FROM contributors
        """)
        all_contributors = cursor.fetchall()
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return render_template('error.html', contributors="Database connection failed.")
    except Exception as e:
        print(f"Unexpected Error: {e}")
        return render_template('error.html', contributors="An unexpected error occurred.")
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

    return render_template('admin_manage_contributors.html', contributors=all_contributors)



# add contributor

@app.route('/admin-add_contributor', methods=['GET', 'POST'])
@login_required
def add_contributor():
    if request.method == 'POST':
        nickname = request.form['nickname']
        username = request.form['username']
        commentary = request.form['commentary']
        custom_nickname = request.form['custom_nickname']
        user_image_url = 'static/img/contributor/default.png' # default image

        # Check if there is an uploaded file
        if 'user_image' in request.files:
            file = request.files['user_image']
            if file and allowed_file(file.filename):
                # Generate a unique name to avoid conflicts
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user_image_url = f'static/img/contributor/{filename}'

        try:
            connection = get_db_connection(db_type="asuka")
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO contributors (nickname, username, commentary, user_image, custom_nickname) 
                VALUES (%s, %s, %s, %s, %s)
            """, (nickname, username, commentary, user_image_url, custom_nickname))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', contributor="Error adding contributor.")
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('admin_manage_contributors'))

    return render_template('admin_add_contributor.html')



# update contributor

@app.route('/admin-edit_contributor/<int:contributor_id>', methods=['GET', 'POST'])
@login_required
def edit_contributor(contributor_id):
    if request.method == 'POST':
        nickname = request.form['nickname']
        username = request.form['username']
        commentary = request.form['commentary']
        custom_nickname = request.form['custom_nickname']
        
        # Get the current image of the contributor
        contributor = execute_query("asuka", """
            SELECT user_image FROM contributors WHERE id = %s
        """, (contributor_id,))
        user_image_url = contributor[0]['user_image']

        # Check if a file is uploaded
        if 'user_image' in request.files:
            file = request.files['user_image']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user_image_url = f'static/img/contributor/{filename}'

        try:
            connection = get_db_connection(db_type="asuka")
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE contributors 
                SET nickname=%s, username=%s, commentary=%s, user_image=%s, custom_nickname=%s 
                WHERE id=%s
            """, (nickname, username, commentary, user_image_url, custom_nickname, contributor_id))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', contributor="Error updating contributor.")
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('admin_manage_contributors'))

    contributor = execute_query("asuka", """
        SELECT id, nickname, username, commentary, user_image, custom_nickname 
        FROM contributors WHERE id = %s
    """, (contributor_id,))
    
    return render_template('admin_edit_contributor.html', contributor=contributor[0])



# delete contributor

@app.route('/admin-delete_contributor/<int:contributor_id>', methods=['POST'])
@login_required
def delete_contributor(contributor_id):
    try:
        connection = get_db_connection(db_type="asuka")
        cursor = connection.cursor()
        cursor.execute("DELETE FROM contributors WHERE id = %s", (contributor_id,))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', contributor="Error deleting contributor.")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('admin_manage_contributors'))

# contributions system

# get all contributions

@app.route('/admin-contributions/<int:contributor_id>')
@login_required
def manage_contributions(contributor_id):
    
    # Get the name and id of the contributor
    contributor = execute_query("asuka", """
        SELECT id, nickname FROM contributors WHERE id = %s
    """, (contributor_id,))
    
    if not contributor:
        return render_template('error.html', message="Contributor not found.")

    # Get contributions from contributor
    contributions = execute_query("asuka", """
        SELECT id, contribution FROM contributions WHERE contributor_id = %s
    """, (contributor_id,))

    return render_template('admin_manage_contributions.html', contributor=contributor[0], contributions=contributions)



# add a contribution

@app.route('/admin-add_contribution/<int:contributor_id>', methods=['GET', 'POST'])
@login_required
def add_contribution(contributor_id):
    if request.method == 'POST':
        contribution_text = request.form['contribution']

        try:
            connection = get_db_connection(db_type="asuka")
            cursor = connection.cursor()
            cursor.execute("""
                INSERT INTO contributions (contributor_id, contribution) 
                VALUES (%s, %s)
            """, (contributor_id, contribution_text))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', message="Error adding contribution.")
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('manage_contributions', contributor_id=contributor_id))

    return render_template('admin_add_contribution.html', contributor_id=contributor_id)

# edit contribution

@app.route('/admin-edit_contribution/<int:contribution_id>', methods=['GET', 'POST'])
@login_required
def edit_contribution(contribution_id):
    if request.method == 'POST':
        contribution_text = request.form['contribution']

        try:
            connection = get_db_connection(db_type="asuka")
            cursor = connection.cursor()
            cursor.execute("""
                UPDATE contributions 
                SET contribution = %s 
                WHERE id = %s
            """, (contribution_text, contribution_id))
            connection.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return render_template('error.html', message="Error updating contribution.")
        finally:
            cursor.close()
            connection.close()

        return redirect(url_for('manage_contributions', contributor_id=request.form['contributor_id']))

    # Get contribution by Id
    contribution = execute_query("asuka", """
        SELECT id, contribution, contributor_id FROM contributions WHERE id = %s
    """, (contribution_id,))
    
    # Make sure the contribution exists
    if not contribution:
        return render_template('error.html', message="Contribution not found.")

    return render_template('admin_edit_contribution.html', contribution=contribution[0])


# delete contribution

@app.route('/admin-delete_contribution/<int:contribution_id>', methods=['POST'])
@login_required
def delete_contribution(contribution_id):
    try:
        connection = get_db_connection(db_type="asuka")
        cursor = connection.cursor()
        cursor.execute("""
            DELETE FROM contributions WHERE id = %s
        """, (contribution_id,))
        connection.commit()
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return render_template('error.html', message="Error deleting contribution.")
    finally:
        cursor.close()
        connection.close()

    return redirect(url_for('manage_contributions', contributor_id=request.form['contributor_id']))





# start system

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True)
