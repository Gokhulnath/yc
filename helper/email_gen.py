import os
import psycopg2
from dotenv import load_dotenv
import math

# Load environment variables from .env file
load_dotenv()

# Database connection details
DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_PORT = int(os.getenv("DB_PORT", "5432"))

# Maximum emails per file
MAX_EMAILS_PER_FILE = 450


def generate_emails():
    connection = None
    try:
        # Connect to the database
        connection = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )

        print("Database connection successful!")

        # Create a cursor
        cursor = connection.cursor()

        # Get all companies with their domains
        cursor.execute("SELECT id, company_name, domain FROM companies WHERE domain IS NOT NULL")
        companies = cursor.fetchall()

        # Initialize email list
        all_emails = []

        # Process each company
        for company_id, company_name, domain in companies:
            if domain and domain.strip():
                # Add founders email for each company
                founders_email = f"founders@{domain}"
                all_emails.append(founders_email)

                # Get people associated with this company
                cursor.execute("SELECT name FROM people WHERE company_id = %s", (company_id,))
                people = cursor.fetchall()

                # Process each person
                for person in people:
                    name = person[0]
                    if name and name.strip():
                        # Extract first name (assuming the first word is the first name)
                        first_name = name.split()[0].lower()
                        # Remove any special characters
                        first_name = ''.join(c for c in first_name if c.isalnum())

                        if first_name:
                            person_email = f"{first_name}@{domain}"
                            all_emails.append(person_email)

        # Calculate how many files we need
        num_files = math.ceil(len(all_emails) / MAX_EMAILS_PER_FILE)

        # Write emails to files
        for i in range(num_files):
            start_idx = i * MAX_EMAILS_PER_FILE
            end_idx = min((i + 1) * MAX_EMAILS_PER_FILE, len(all_emails))

            file_name = f"emails_{i + 1}.txt"
            with open(file_name, 'w') as f:
                for email in all_emails[start_idx:end_idx]:
                    f.write(f"{email}\n")

            print(f"Created {file_name} with {end_idx - start_idx} emails")

        print(f"Email generation complete. Created {num_files} files with a total of {len(all_emails)} emails.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if connection:
            connection.close()
            print("Database connection closed.")


if __name__ == "__main__":
    generate_emails()
