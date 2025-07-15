from flask import Flask, render_template, request, flash, redirect, url_for
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Email
from flask_mail import Mail, Message
import os


# Form class for contact form
class ContactForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    subject = StringField('Subject', validators=[DataRequired()])
    message = TextAreaField('Message', validators=[DataRequired()])
    submit = SubmitField('Send')


def configure_mail(app):
    """Configure Flask-Mail with the application"""
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')
    app.config['RECIPIENT_EMAIL'] = os.environ.get('RECIPIENT_EMAIL')

    # If any required config is missing, raise an error
    required_configs = ['MAIL_USERNAME', 'MAIL_PASSWORD', 'RECIPIENT_EMAIL']
    missing_configs = [config for config in required_configs if not app.config.get(config)]
    if missing_configs:
        print(f"Warning: Missing required email configurations: {', '.join(missing_configs)}")

    return Mail(app)


# def register_email_form_routes(app, mail):
#     """Register routes related to the contact form"""
#
#     @app.route('/contact', methods=['GET', 'POST'])
#     def contact():
#         # Explicitly create a new form instance
#         form = ContactForm()
#
#         # Set secret key if not set (needed for CSRF protection)
#         if not app.config.get('SECRET_KEY'):
#             app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-for-csrf')
#
#         # When form is submitted and valid
#         if request.method == 'POST' and form.validate_on_submit():
#             try:
#                 # Create the email message
#                 msg = Message(
#                     subject=f"Contact Form: {form.subject.data}",
#                     recipients=[app.config['RECIPIENT_EMAIL']],
#                     body=f"""
#                     Name: {form.name.data}
#                     Email: {form.email.data}
#
#                     {form.message.data}
#                     """,
#                     reply_to=form.email.data
#                 )
#
#                 # Send the email
#                 mail.send(msg)
#
#                 flash('Your message has been sent successfully!', 'success')
#                 return redirect(url_for('contact'))
#
#             except Exception as e:
#                 flash(f'An error occurred: {str(e)}', 'danger')
#                 print(f"Email error: {str(e)}")  # Log the error
#
#         # Always pass the form to the template
#         return render_template('contact.html', form=form)


def init_email_form_handler(app):
    """Initialize the email form handler with the Flask app"""
    # Set a secret key for CSRF protection (required for WTForms)
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-for-csrf')
        print("Warning: Using default SECRET_KEY. For production, set a secure SECRET_KEY.")

    # Enable CSRF protection
    app.config['WTF_CSRF_ENABLED'] = True

    # Configure Flask-Mail
    mail = configure_mail(app)

    # Register routes
    # register_email_form_routes(app, mail)

    return mail