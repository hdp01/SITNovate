from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.security import generate_password_hash, check_password_hash
import requests
import os
from werkzeug.utils import secure_filename
import google.generativeai as genai
import json

# Initialize Flask app
app = Flask(__name__)

# Configure Secret Key
app.config['SECRET_KEY'] = "your-secret-key"

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize CSRF Protection
csrf = CSRFProtect(app)

# Initialize Database
db = SQLAlchemy(app)

# Configure Gemini AI
genai.configure(api_key="AIzaSyDL7fi3LJP5Z1RVY33WabBvBvKkHNGnI0E")

# AWS Lambda Endpoint
AWS_LAMBDA_ENDPOINT = "https://z1fw0ychtd.execute-api.ap-south-1.amazonaws.com/dev/real-images-syntaxslayers/"

# Define User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)  # Increased length for hashing

# Define Signup Form
class SignupForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(min=2, max=100)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign Up')

# Define Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Login')

# Create database tables
with app.app_context():
    db.create_all()

# Index Route
@app.route('/')
def index():
    return render_template('index.html')

# Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    form = SignupForm()
    
    if form.validate_on_submit():
        hashed_password = generate_password_hash(form.password.data, method='pbkdf2:sha256', salt_length=8)
        
        new_user = User(
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=hashed_password,
        )
        db.session.add(new_user)
        db.session.commit()
        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html', form=form)

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()

        if user and check_password_hash(user.password, form.password.data):
            session['user_id'] = user.id  # Store user session
            flash('Login successful!', 'success')
            return redirect(url_for('upload_page'))  # Redirect to upload page after login
        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html', form=form)

# Upload Page Route
@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    if 'user_id' not in session:
        flash('Please log in to access this page.', 'warning')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Check if the file is present in the request
        if 'file' not in request.files:
            flash('No file uploaded.', 'danger')
            return redirect(request.url)

        file = request.files['file']

        # Check if the file is empty
        if file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(request.url)

        # Secure the filename
        filename = secure_filename(file.filename)

        # Save the file temporarily
        uploads_dir = os.path.join(app.root_path, 'uploads')
        os.makedirs(uploads_dir, exist_ok=True)
        file_path = os.path.join(uploads_dir, filename)
        file.save(file_path)

        # Send the file to AWS Lambda for processing
        try:
            # Upload the image to the AWS Lambda API
            upload_url = AWS_LAMBDA_ENDPOINT
            with open(file_path, 'rb') as f:
                response = requests.post(upload_url, files={'file': f})

            if response.status_code != 200:
                flash('Failed to upload image to AWS Lambda.', 'danger')
                return redirect(request.url)

            # Retrieve the processed image URL from the response
            processed_url = response.json().get('processedUrl')
            if not processed_url:
                flash('Failed to retrieve processed image URL.', 'danger')
                return redirect(request.url)

            # Save the processed image URL in the session for display
            session['processed_image'] = processed_url
            flash('Image uploaded and processed successfully!', 'success')
            return redirect(url_for('upload_page'))

        except Exception as e:
            print(f"Error: {e}")
            flash('An error occurred while processing the image.', 'danger')
            return redirect(request.url)

    # Render the upload page with the processed image (if any)
    processed_image = session.pop('processed_image', None)
    return render_template('uploadpage.html', processed_image=processed_image)

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Clear user session
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# Gemini AI Processing Route
@app.route('/process-request', methods=['POST'])
def process_request():
    try:
        data = request.json
        user_query = data['query']
        
        # Generate parameters with Gemini
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(PROMPT_TEMPLATE.format(query=user_query))
        
        # Clean response
        cleaned = response.text.replace('```json', '').replace('```', '').strip()
        params = json.loads(cleaned)
        
        return jsonify(params)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# AWS Lambda Upload Route
@app.route('/upload-to-aws', methods=['POST'])
def upload_to_aws():
    try:
        image_file = request.files['image']
        params = request.form.to_dict()
        
        # Prepare AWS request
        filename = image_file.filename
        aws_url = f"{AWS_LAMBDA_ENDPOINT}{filename}"
        
        # Send to AWS Lambda
        response = requests.put(
            aws_url,
            data=image_file.read(),
            headers={
                'Content-Type': image_file.mimetype,
                'X-Processing-Params': json.dumps(params)
            }
        )
        
        return jsonify({
            "status": response.status_code,
            "message": "Image sent to AWS Lambda",
            "response": response.text
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Run the app
if __name__ == '__main__':
    # Create uploads and processed directories if they don't exist
    os.makedirs('uploads', exist_ok=True)
    os.makedirs('processed', exist_ok=True)
    app.run(debug=True)