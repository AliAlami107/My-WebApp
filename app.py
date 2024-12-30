from flask import Flask, render_template, request, flash, redirect, url_for, session, jsonify
import csv
import os
from functools import wraps
from datetime import datetime
import json
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# Add these configurations at the top of app.py
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
MAX_IMAGES = 8
MIN_IMAGES = 3

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'  # You need to set up an email to send from
app.config['MAIL_PASSWORD'] = 'your-app-password'     # You'll need to generate an App Password
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@gmail.com'

mail = Mail(app)

# Create uploads directory if it doesn't exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Create database files if they don't exist
def init_databases():
    # For agencies
    if not os.path.exists('agencies.csv'):
        with open('agencies.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['email', 'password', 'agency_name'])

    # Updated talents.csv structure
    if not os.path.exists('talents.csv'):
        with open('talents.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([
                'email', 'password', 'name', 'age', 'role', 'bio',
                'height', 'weight', 'eye_color', 'hair_color', 'race',
                'city', 'country', 'image'
            ])

    # For storing matches and profile views
    if not os.path.exists('interactions.csv'):
        with open('interactions.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['agency_email', 'talent_email', 'interaction_type', 'timestamp'])

init_databases()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        account_type = request.form.get('account_type')
        
        if account_type == 'agency':
            agency_name = request.form.get('agency_name')
            
            # Check if agency already exists
            with open('agencies.csv', 'r') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row[0] == email:
                        flash('Email already exists!', 'error')
                        return redirect(url_for('signup'))
            
            # Add new agency
            with open('agencies.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([email, password, agency_name])
        
        else:  # talent account
            name = request.form.get('name')
            age = request.form.get('age')
            role = request.form.get('role')
            bio = request.form.get('bio')
            image = request.form.get('image', 'https://picsum.photos/400/500')  # default image
            
            # Check if talent already exists
            with open('talents.csv', 'r') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row[0] == email:
                        flash('Email already exists!', 'error')
                        return redirect(url_for('signup'))
            
            # Add new talent
            with open('talents.csv', 'a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([email, password, name, age, role, bio, image])
        
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        account_type = request.form.get('account_type')
        
        file_to_check = 'agencies.csv' if account_type == 'agency' else 'talents.csv'
        
        with open(file_to_check, 'r') as file:
            reader = csv.reader(file)
            next(reader)
            for row in reader:
                if row[0] == email and row[1] == password:
                    session['user'] = email
                    session['account_type'] = account_type
                    if account_type == 'agency':
                        return redirect(url_for('profiles'))
                    else:
                        return redirect(url_for('talent_dashboard'))
        
        flash('Invalid email or password!', 'error')
        return redirect(url_for('login'))
    
    return render_template('login.html')

@app.route('/profiles')
@login_required
def profiles():
    if session.get('account_type') != 'agency':
        return redirect(url_for('talent_dashboard'))
    
    talents = []
    with open('talents.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            # Get all images for the talent
            images = row[13].split(',') if len(row) > 13 and row[13] else []
            # Use first image as profile picture, or default if none exists
            profile_image = images[0] if images else 'https://picsum.photos/400/500'
            
            talents.append({
                'id': row[0],  # email as ID
                'name': row[2],
                'age': row[3],
                'role': row[4],
                'bio': row[5],
                'height': row[6] if len(row) > 6 else '',
                'weight': row[7] if len(row) > 7 else '',
                'eye_color': row[8] if len(row) > 8 else '',
                'hair_color': row[9] if len(row) > 9 else '',
                'race': row[10] if len(row) > 10 else '',
                'city': row[11] if len(row) > 11 else '',
                'country': row[12] if len(row) > 12 else '',
                'image': profile_image,
                'all_images': images
            })
    
    return render_template('profiles.html', profiles=talents)

@app.route('/talent_dashboard')
@login_required
def talent_dashboard():
    if session.get('account_type') != 'talent':
        return redirect(url_for('profiles'))
    
    # Get talent's information
    talent_info = None
    with open('talents.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            if row[0] == session['user']:
                # Split the images string into a list
                images = row[13].split(',') if len(row) > 13 and row[13] else []
                # Use the first image as profile picture, or default if none exists
                profile_image = images[0] if images else 'https://picsum.photos/400/500'
                
                talent_info = {
                    'email': row[0],
                    'name': row[2],
                    'age': row[3],
                    'role': row[4],
                    'bio': row[5],
                    'height': row[6] if len(row) > 6 else '',
                    'weight': row[7] if len(row) > 7 else '',
                    'eye_color': row[8] if len(row) > 8 else '',
                    'hair_color': row[9] if len(row) > 9 else '',
                    'race': row[10] if len(row) > 10 else '',
                    'city': row[11] if len(row) > 11 else '',
                    'country': row[12] if len(row) > 12 else '',
                    'image': profile_image,  # Use the first image as profile picture
                    'all_images': images  # Keep all images for reference
                }
                break
    
    # Get statistics
    profile_views = 0
    matches = []
    recent_activities = []
    
    with open('interactions.csv', 'r') as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            agency_email, talent_email, interaction_type, timestamp = row
            
            if talent_email == session['user']:
                if interaction_type == 'view':
                    profile_views += 1
                elif interaction_type == 'match':
                    matches.append({
                        'agency_email': agency_email,
                        'timestamp': timestamp
                    })
                
                # Add to recent activities
                recent_activities.append({
                    'type': interaction_type,
                    'agency_email': agency_email,
                    'timestamp': datetime.fromisoformat(timestamp)
                })
    
    # Sort activities by timestamp (most recent first)
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    recent_activities = recent_activities[:5]  # Keep only 5 most recent
    
    return render_template('talent_dashboard.html',
                         talent=talent_info,
                         profile_views=profile_views,
                         matches=len(matches),
                         recent_activities=recent_activities)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/swipe', methods=['POST'])
@login_required
def swipe():
    if session.get('account_type') != 'agency':
        return {'error': 'Unauthorized'}, 401
        
    data = request.json
    talent_email = data.get('talent_id')  # Using email as ID
    direction = data.get('direction')
    
    if direction == 'right':
        with open('interactions.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([session['user'], talent_email, 'match', datetime.now().isoformat()])
    
    return {'status': 'success'}

# Add new route for editing profile
@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if session.get('account_type') != 'talent':
        return redirect(url_for('profiles'))
    
    if request.method == 'POST':
        # Get user's upload directory
        user_folder = get_user_upload_folder(session['user'])
        
        # Handle image uploads
        uploaded_files = request.files.getlist('photos')
        valid_images = []
        
        # Get existing images
        existing_images = request.form.getlist('existing_images')
        
        # Process new uploads
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{int(time.time())}_{file.filename}")
                filepath = os.path.join(user_folder, filename)
                file.save(filepath)
                # Store relative path in database
                relative_path = f'/static/uploads/{secure_filename(session["user"])}/{filename}'
                valid_images.append(relative_path)
        
        # Combine existing and new images
        all_images = existing_images + valid_images
        
        if len(all_images) < MIN_IMAGES:
            flash(f'Please upload at least {MIN_IMAGES} images', 'error')
            return redirect(url_for('edit_profile'))
        
        if len(all_images) > MAX_IMAGES:
            flash(f'Maximum {MAX_IMAGES} images allowed', 'error')
            return redirect(url_for('edit_profile'))
        
        # Update database
        talents = []
        with open('talents.csv', 'r') as file:
            reader = csv.reader(file)
            header = next(reader)
            talents = list(reader)
        
        for i, talent in enumerate(talents):
            if talent[0] == session['user']:
                talents[i] = [
                    talent[0],  # email
                    talent[1],  # password
                    request.form.get('name'),
                    request.form.get('age'),
                    request.form.get('role'),
                    request.form.get('bio'),
                    request.form.get('height'),
                    request.form.get('weight'),
                    request.form.get('eye_color'),
                    request.form.get('hair_color'),
                    request.form.get('race'),
                    request.form.get('city'),
                    request.form.get('country'),
                    ','.join(all_images)  # Store all image paths
                ]
                break
        
        with open('talents.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(header)
            writer.writerows(talents)
        
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('talent_dashboard'))

    # GET request handling remains the same
    current_profile = None
    with open('talents.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        for row in reader:
            if row[0] == session['user']:
                current_profile = {
                    'email': row[0],
                    'name': row[2],
                    'age': row[3],
                    'role': row[4],
                    'bio': row[5],
                    'height': row[6] if len(row) > 6 else '',
                    'weight': row[7] if len(row) > 7 else '',
                    'eye_color': row[8] if len(row) > 8 else '',
                    'hair_color': row[9] if len(row) > 9 else '',
                    'race': row[10] if len(row) > 10 else '',
                    'city': row[11] if len(row) > 11 else '',
                    'country': row[12] if len(row) > 12 else '',
                    'images': row[13].split(',') if len(row) > 13 and row[13] else []
                }
                break
    
    return render_template('edit_profile.html', profile=current_profile)

@app.route('/delete_image', methods=['POST'])
@login_required
def delete_image():
    if session.get('account_type') != 'talent':
        return {'error': 'Unauthorized'}, 401
    
    image_path = request.json.get('image_path')
    if not image_path:
        return {'error': 'No image path provided'}, 400
    
    # Verify the image belongs to the current user
    user_folder = secure_filename(session['user'])
    if user_folder not in image_path:
        return {'error': 'Unauthorized access'}, 403
    
    # Read current talent data
    talents = []
    with open('talents.csv', 'r') as file:
        reader = csv.reader(file)
        header = next(reader)
        talents = list(reader)
    
    # Update images for the talent
    for i, talent in enumerate(talents):
        if talent[0] == session['user']:
            current_images = talent[13].split(',') if talent[13] else []
            
            if image_path in current_images:
                if len(current_images) <= MIN_IMAGES:
                    return {'error': f'You must maintain at least {MIN_IMAGES} images'}, 400
                
                current_images.remove(image_path)
                talents[i][13] = ','.join(current_images)
                
                # Delete the actual file
                file_path = os.path.join('.', image_path.lstrip('/'))
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Error deleting file: {e}")
                
                # Write back to CSV
                with open('talents.csv', 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerow(header)
                    writer.writerows(talents)
                
                return {
                    'success': True,
                    'remaining_images': len(current_images),
                    'message': 'Image deleted successfully'
                }
    
    return {'error': 'Image not found'}, 404

@app.route('/send_message', methods=['POST'])
def send_message():
    try:
        name = request.form.get('name')
        email = request.form.get('email')
        subject = request.form.get('subject')
        message = request.form.get('message')

        # Create email content
        email_content = f"""
        New message from CastSwipe Contact Form:
        
        From: {name}
        Email: {email}
        Subject: {subject}
        
        Message:
        {message}
        """

        # Create and send email
        msg = Message(
            subject=f"CastSwipe Contact Form: {subject}",
            recipients=['kasperalami00@gmail.com'],
            body=email_content
        )
        
        mail.send(msg)
        
        return jsonify({'success': True, 'message': 'Message sent successfully!'})
    except Exception as e:
        print(f"Error sending email: {e}")
        return jsonify({'success': False, 'message': 'Failed to send message. Please try again.'}), 500

# Add function to create user-specific directory
def get_user_upload_folder(user_email):
    # Create a safe directory name from the email
    safe_email = secure_filename(user_email)
    user_folder = os.path.join(UPLOAD_FOLDER, safe_email)
    if not os.path.exists(user_folder):
        os.makedirs(user_folder)
    return user_folder

if __name__ == '__main__':
    app.run(debug=True) 