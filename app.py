from flask import Flask, request, jsonify, render_template, send_from_directory, abort, Response, make_response, url_for, redirect, flash
from werkzeug.utils import secure_filename
import requests
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email
import os
import json
import hashlib
import csv
from datetime import datetime, timedelta
import io
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env file
from email_form_handler import init_email_form_handler, ContactForm
from flask_mail import Mail, Message
app = Flask(__name__)
mail = init_email_form_handler(app)

SLACK_WEBHOOK_URL = os.environ.get('SLACK_WEBHOOK_URL')

app.config['REPORTS_FOLDER'] = os.path.join(app.root_path, 'reports')
app.config['USERS_FILE'] = os.path.join(app.root_path, 'users.json')
app.config['STATIC_DATA'] = os.path.join(app.root_path, 'static', 'data')
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

# Create necessary directories if they don't exist
os.makedirs(app.config['REPORTS_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_DATA'], exist_ok=True)

credentials = os.environ.get('VALID_CREDENTIALS')
VALID_CREDENTIALS = json.loads(credentials)

@app.route('/verify-credentials', methods=['POST'])
def verify_credentials():
    """Verify user credentials."""
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400

    # Check if credentials are valid
    if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
        return jsonify({'success': True, 'message': 'Authentication successful'})
    else:
        return jsonify({'success': False, 'message': 'Invalid username or password'}), 401


def check_auth(username, password):
    """
    Check if the provided username and password match the credentials in the flat file.

    Args:
        username: The username to check
        password: The password to check

    Returns:
        Boolean indicating if authentication was successful
    """
    try:
        with open(app.config['USERS_FILE'], 'r') as f:
            users = json.load(f)

        if username in users:
            # Simple hash comparison - in production, use a proper password hashing library
            stored_hash = users[username]['password_hash']
            # Create a simple hash for comparison
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            return password_hash == stored_hash

        return False
    except (FileNotFoundError, json.JSONDecodeError):
        app.logger.error(f"Error reading users file: {app.config['USERS_FILE']}")
        return False

class ContactForm(FlaskForm):
    """Contact form model."""
    name = StringField('Your Name', validators=[DataRequired()])
    email = StringField('Your Email', validators=[DataRequired(), Email(message='Enter a valid email.')])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send Message')

class DataRequestForm(FlaskForm):
    """Data request form model."""
    email = StringField('Email Address', validators=[DataRequired(), Email()])
    data_points = TextAreaField('Data Points', validators=[DataRequired()])
    submit = SubmitField('Submit Request')

def send_to_slack(name, email, subject, message):
    """
    Formats the form data and sends it to a Slack channel via a webhook.
    """
    if not SLACK_WEBHOOK_URL:
        # Log an error if the webhook URL is not configured.
        app.logger.error("SLACK_WEBHOOK_URL is not configured.")
        return False

    # This is the message payload that Slack's API expects.
    # We use "blocks" for a richer message format.
    slack_payload = {
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":envelope_with_arrow: *New WNBR Inquiry Submission*"
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Name:*\n{name}"},
                    {"type": "mrkdwn", "text": f"*Email:*\n<{email}|{email}>"}
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Subject:*\n{subject}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Message:*\n{message}"
                }
            }
        ]
    }

    try:
        # Send the POST request to the Slack webhook URL.
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return True
    except requests.exceptions.RequestException as e:
        # Log any exceptions that occur during the request.
        app.logger.error(f"Error sending message to Slack: {e}")
        return False

def send_data_request_to_slack(email, data_points):
    """
    Formats the data request form data and sends it to a Slack channel.
    """
    if not SLACK_WEBHOOK_URL:
        app.logger.error("SLACK_WEBHOOK_URL is not configured.")
        return False

    slack_payload = {
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": ":bar_chart: *New Data Report Request*"}},
            {"type": "divider"},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Requester Email:*\n<{email}|{email}>"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": f"*Requested Data Points:*\n{data_points}"}}
        ]
    }
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=slack_payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error sending message to Slack: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    """
    Handles both displaying the form (GET) and processing the submission (POST).
    """
    form = ContactForm()
    # The validate_on_submit() method checks if it's a POST request and if the data is valid.
    if form.validate_on_submit():
        # Retrieve the validated data from the form object.
        name = form.name.data
        email = form.email.data
        subject = form.subject.data
        message = form.message.data

        # Send the data to your Slack channel.
        if send_to_slack(name, email, subject, message):
            flash('Thank you for your message. It has been sent!', 'success')
        else:
            flash('Sorry, there was an error sending your message. Please try again later.', 'danger')

        # It's good practice to redirect after a successful POST to prevent duplicate submissions.
        # However, for this example, we'll just re-render the template.
        return render_template('index.html', form=ContactForm())

    # If it's a GET request or the form is invalid, just render the template with the form.
    return render_template('index.html', form=form)
@app.route('/biobank/index')
def biobankindex():
    return render_template("/biobank/index.html", page_title="Biobank Index")


@app.route('/biobank/team')
def biobankteam():
    return render_template("/biobank/team.html", page_title="Biobank Team")


@app.route('/biobank/collection')
def biobankcollection():
    return render_template("/biobank/collection.html", page_title="Sample Collection")


@app.route('/biobank/samplerequest')
def biobanksamplerequest():
    return render_template("/biobank/samplerequest.html", page_title="Request Samples")


@app.route('/biobank/lims')
def biobanklims():
    return render_template("/biobank/lims.html", page_title="LIMS information")


@app.route('/biobank/dashboard')
def biobankdashboard():
    return render_template("/biobank/dashboard.html", page_title="Sample Dashboard")


@app.route('/biobank/team2')
def biobankteam2():
    return render_template("/biobank/team2.html")


@app.route('/dataservices/index', methods=['GET', 'POST'])
def dataservicesindex():
    # Make sure sample data is initialized
    initialize_sample_data()
    form = DataRequestForm()
    if form.validate_on_submit():
        if send_data_request_to_slack(form.email.data, form.data_points.data):
            flash('Your data request has been submitted successfully!', 'success')
        else:
            flash('There was an error submitting your request. Please try again later.', 'danger')
        return redirect(url_for('data_request'))
    return render_template("/dataservices/index.html", page_title="Data Services", form=form)


@app.route('/dataservices/datarequest')
def dataservicesrequest():
    return render_template("/dataservices/datarequest.html", page_title="Request Data")


@app.route('/dataservices/lims')
def dataserviceslims():
    return render_template("/dataservices/lims.html", page_title="LIMS Information")


@app.route('/dataservices/useradmin')
def dataservicesuseradmin():
    return render_template("/dataservices/useradmin.html", page_title="User Admin")


@app.route('/dataservices/dashboard')
def dataservicesdashboard():
    return render_template("/dataservices/dashboard.html", page_title="Data Dash")


@app.route('/dataservices/reports')
def dataservicesreports():
    return render_template("/dataservices/reports.html", page_title="Reports")


@app.route('/download/<filename>', methods=['GET', 'POST'])
def download_with_auth(filename):
    """Handle authenticated file downloads."""
    # Secure the filename to prevent directory traversal attacks
    filename = secure_filename(filename)

    # Check authentication
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Verify credentials
        if username in VALID_CREDENTIALS and VALID_CREDENTIALS[username] == password:
            # Authentication successful, process download
            try:
                file_path = os.path.join(app.config['REPORTS_FOLDER'], filename)

                # Check if file exists
                if not os.path.isfile(file_path):
                    # For demonstration purposes, if the file doesn't exist,
                    # we'll create a simple text file
                    if not os.path.exists(app.config['REPORTS_FOLDER']):
                        os.makedirs(app.config['REPORTS_FOLDER'])

                    with open(file_path, 'w') as f:
                        f.write(f"This is a sample report file: {filename}\n")
                        f.write("Created for demonstration purposes.")

                return send_from_directory(
                    directory=app.config['REPORTS_FOLDER'],
                    path=filename,
                    as_attachment=True
                )
            except Exception as e:
                app.logger.error(f"Download error: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': 'Error processing download. Please contact an administrator.'
                }), 500
        else:
            # Authentication failed
            return jsonify({
                'success': False,
                'message': 'Invalid credentials. Access denied.'
            }), 401

    # GET requests should be handled too - redirect to authentication
    return jsonify({
        'success': False,
        'message': 'Authentication required to download files.'
    }), 401


@app.route('/faq')
def faq():
    return render_template("/faq.html", page_title="WNBR FAQ")


@app.route('/ms/index')
def msindex():
    return render_template("/ms/index.html")


@app.route('/pd/index')
def pdindex():
    return render_template("/pd/index.html")


@app.route('/als/index')
def alsindex():
    return render_template("/als/index.html")


@app.route('/alzheimers/index')
def alzheimersindex():
    return render_template("/alzheimers/index.html")


@app.route('/api/sample-data', methods=['GET'])
def get_sample_data():
    """API endpoint to get sample data with optional filters."""
    try:
        # Initialize sample data if it doesn't exist
        initialize_sample_data()

        # Parse filter parameters
        disease_filter = request.args.get('disease', 'all')
        sample_filter = request.args.get('sample_type', 'all')
        date_filter = request.args.get('date_range', 'all')

        # Load the CSV file
        csv_path = os.path.join(app.config['STATIC_DATA'], 'WNBR_Sample_Collection_Data.csv')

        with open(csv_path, 'r', newline='') as csvfile:
            # Create a CSV reader
            reader = csv.DictReader(csvfile)

            # Convert to list of dictionaries
            all_samples = list(reader)

            # Apply filters
            filtered_samples = all_samples

            if disease_filter != 'all':
                filtered_samples = [sample for sample in filtered_samples
                                    if sample['disease_type'] == disease_filter]

            if sample_filter != 'all':
                filtered_samples = [sample for sample in filtered_samples
                                    if sample['sample_type'] == sample_filter]

            if date_filter != 'all':
                days = int(date_filter)
                cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
                filtered_samples = [sample for sample in filtered_samples
                                    if sample['collection_date'] >= cutoff_date]

        # Write the filtered samples to a CSV string
        output = io.StringIO()
        if filtered_samples:
            writer = csv.DictWriter(output, fieldnames=filtered_samples[0].keys())
            writer.writeheader()
            writer.writerows(filtered_samples)

        # Return the CSV as a response
        return Response(output.getvalue(), mimetype='text/csv')

    except Exception as e:
        app.logger.error(f"Error processing sample data: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Error processing sample data: {str(e)}'
        }), 500


def initialize_sample_data():
    """Initialize the sample data CSV."""
    try:
        csv_path = os.path.join(app.config['STATIC_DATA'], 'WNBR_Sample_Collection_Data.csv')

        # Check if the CSV file already exists
        if not os.path.exists(csv_path):
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)

            # Define sample data with 25 entries
            full_sample_data = [
                {
                    'sample_id': f'WNB{i + 1:03d}',
                    'patient_id': f'PT{10045 + i}',
                    'collection_date': f'2025-{(i // 7) + 1:02d}-{(i % 28) + 1:02d}',
                    'disease_type': ['Multiple Sclerosis', 'Parkinson\'s Disease', 'Alzheimer\'s Disease', 'ALS'][
                        i % 4],
                    'sample_type': ['Serum', 'Plasma', 'CSF', 'DNA'][i % 4],
                    'volume_ml': round(1.5 + (i % 7) * 0.5, 1),
                    'processing_status': ['Processed', 'Processing', 'Awaiting Processing'][min(2, i // 10)],
                    'storage_location': f'Freezer-{chr(65 + (i % 4))}{(i % 10) + 1}',
                    'sex': ['Female', 'Male'][i % 2],
                    'age': 28 + (i % 60),
                    'race': ['White', 'African American', 'Asian', 'Hispanic'][i % 4]
                } for i in range(25)
            ]

            # Write to CSV file
            with open(csv_path, 'w', newline='') as csvfile:
                fieldnames = full_sample_data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

                writer.writeheader()
                for row in full_sample_data:
                    writer.writerow(row)

            app.logger.info(f"Sample data initialized successfully with {len(full_sample_data)} records")
            return True
        else:
            app.logger.info("Sample data file already exists")
            return True

    except Exception as e:
        app.logger.error(f"Error initializing sample data: {str(e)}")
        return False


# Register URL rules for existing functions
app.add_url_rule('/verify-credentials', view_func=verify_credentials, methods=['POST'])
app.add_url_rule('/download/<filename>', view_func=download_with_auth, methods=['GET', 'POST'])

if __name__ == '__main__':
    # Initialize sample data on startup
    with app.app_context():
        initialize_sample_data()

    app.run(debug=True)