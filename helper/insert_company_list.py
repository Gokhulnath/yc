import psycopg2
import logging

from dotenv import load_dotenv

from helper.database_connector import get_db_params_from_env

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("db_insert.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# Database connection parameters - update these with your actual database credentials

DB_PARAMS = get_db_params_from_env()


def _get_year(batch):
    # Extract the last two characters from the input string
    last_two = batch[-2:]

    # Concatenate "20" to the front
    year = "20" + last_two

    return int(year)


def _get_or_create_batch(cursor, batch_name, batch_link):
    """
    Check if batch exists and return its ID. If not, create it and return the new ID.
    """
    try:
        # Check if batch exists
        cursor.execute(
            "SELECT id FROM batches WHERE batch = %s",
            (batch_name,)
        )
        result = cursor.fetchone()

        if result:
            logger.info(f"Batch '{batch_name}' already exists with ID: {result[0]}")
            return result[0]
        else:
            # Insert new batch

            cursor.execute(
                "INSERT INTO batches (batch, batch_link, year) VALUES (%s, %s, %s) RETURNING id",
                (batch_name, batch_link, _get_year(batch_name))
            )
            batch_id = cursor.fetchone()[0]
            logger.info(f"Created new batch '{batch_name}' with ID: {batch_id}")
            return batch_id
    except Exception as e:
        logger.error(f"Error in get_or_create_batch: {str(e)}")
        raise


def _get_or_create_industry(cursor, industry_name, industry_link):
    """
    Check if industry exists and return its ID. If not, create it and return the new ID.
    """
    try:
        # Check if industry exists
        cursor.execute(
            "SELECT id FROM industries WHERE industry = %s",
            (industry_name,)
        )
        result = cursor.fetchone()

        if result:
            logger.debug(f"Industry '{industry_name}' already exists with ID: {result[0]}")
            return result[0]
        else:
            # Insert new industry
            cursor.execute(
                "INSERT INTO industries (industry, industry_link) VALUES (%s, %s) RETURNING id",
                (industry_name, industry_link)
            )
            industry_id = cursor.fetchone()[0]
            logger.debug(f"Created new industry '{industry_name}' with ID: {industry_id}")
            return industry_id
    except Exception as e:
        logger.error(f"Error in get_or_create_industry: {str(e)}")
        raise


def _insert_company(cursor, company_data, batch_id):
    """
    Insert company data and associate it with industries
    """
    try:
        # Insert company
        cursor.execute(
            """
            INSERT INTO companies 
            (logo, company_name, link, location, short_description, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                company_data['logo'],
                company_data['company_name'],
                company_data['link'],
                company_data['location'],
                company_data['short_description'],
                batch_id
            )
        )
        company_id = cursor.fetchone()[0]
        logger.info(f"Inserted company '{company_data['company_name']}' with ID: {company_id}")

        # Process industries
        for ind in company_data['industry']:
            industry_id = _get_or_create_industry(cursor, ind['type'], ind['link'])

            # Associate company with industry
            cursor.execute(
                """
                INSERT INTO company_industries (company_id, industry_id)
                VALUES (%s, %s)
                """,
                (company_id, industry_id)
            )
            logger.debug(f"Associated company '{company_data['company_name']}' with industry '{ind['type']}'")

        return company_id
    except Exception as e:
        logger.error(f"Error inserting company {company_data['company_name']}: {str(e)}")
        raise

def insert_data(data):
    conn = None
    try:
        # Connect to the database
        logger.info("Connecting to the PostgreSQL database...")
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()

        # Begin transaction
        conn.autocommit = False

        # Get or create batch
        batch_id = _get_or_create_batch(cursor, data['batch'], data['batch_link'])

        # Insert companies
        companies_inserted = 0
        for company in data['companies']:
            try:
                _insert_company(cursor, company, batch_id)
                companies_inserted += 1
            except Exception as e:
                logger.error(f"Error processing company {company.get('company_name', 'unknown')}: {str(e)}")
                # Continue with next company
                continue

        # Commit transaction if everything is successful
        conn.commit()
        logger.info(f"Successfully processed batch '{data['batch']}' with {companies_inserted} companies")

    except Exception as e:
        # Rollback in case of error
        if conn:
            conn.rollback()
        logger.error(f"Error in main process: {str(e)}")
    finally:
        # Close database connection
        if conn:
            conn.close()
            logger.info("Database connection closed.")