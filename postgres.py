from typing import Any, List, Dict, Optional
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncpg
from dotenv import load_dotenv
import os
import sys
import datetime
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("server_module")

from mcp.server.fastmcp import Context, FastMCP

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters from environment variables
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = int(os.getenv('PG_PORT', '5432'))
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
PG_DATABASE = os.getenv('PG_DATABASE', 'postgres')

@asynccontextmanager
# Type-safe application lifespan context manager
async def app_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """Manage application lifecycle with type-safe context"""
    logger.debug("Initializing PostgreSQL database connection")
    conn = None
    
    try:
        conn = await asyncpg.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE
        )
        logger.debug("PostgreSQL connection established successfully")
        yield {"conn": conn}
    except Exception as e:
        logger.error(f"PostgreSQL connection error: {type(e).__name__}: {str(e)}", exc_info=True)
        yield {"conn": None}
    finally:
        if conn:
            logger.debug("Closing PostgreSQL connection")
            await conn.close()

# Initialize FastMCP server with lifespan context
mcp = FastMCP("appointments", lifespan=app_lifespan)



# Define tools for the MCP server: retrieve all data
@mcp.tool()
async def retrieve_all_data(
    ctx: Context,
    table_name: str="agenda",
    columns: Optional[List[str]] = None
) -> List[Dict[str, Any]] | None:
    """
    Retrieve all data from the medical agenda (PostgreSQL table) with proper error handling.
    
    Args:
        table_name: Name of the table to query
        columns: Optional list of specific columns to retrieve. If None, retrieves all columns.
    
    Returns:
        List of dictionaries representing rows, or None if error occurs
    """
    try:
        # Get connection from lifespan context
        conn = ctx.request_context.lifespan_context["conn"]
        
        if conn is None:
            logger.error("Database connection is not available")
            return None
        
        # Build query
        if columns:
            # Sanitize column names to prevent SQL injection
            sanitized_columns = [f'"{col}"' for col in columns]
            columns_str = ", ".join(sanitized_columns)
            if table_name == 'agenda':
                query = f'SELECT {columns_str} FROM "{table_name}" as s1 left join "patients" as s2 on s1.patient_number=s2.patient_number left join appointment_types as s3 on s1.appointment_type=s3.appointment_number'
            else:
                query = f'SELECT {columns_str} FROM "{table_name}"'
        else:
            query = f'SELECT * FROM "{table_name}"'
        
        # Execute query
        rows = await conn.fetch(query)
        
        # Convert to list of dictionaries
        result = [dict(row) for row in rows]
        
        logger.info(f"Successfully retrieved {len(result)} rows from {table_name}")
        return result
            
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error retrieving data from {table_name}: {e}")
        return None



# Define tools for the MCP server: retrieve data with conditions
@mcp.tool()
async def retrieve_data_with_conditions(
    table_name: str,
    ctx: Context,
    where_clause: Optional[str] = None,
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    columns: Optional[List[str]] = None
) -> List[Dict[str, Any]] | None:
    """
    Retrieve data from PostgreSQL table with optional conditions.
    
    Args:
        table_name: Name of the table to query
        where_clause: Optional WHERE clause (without the WHERE keyword)
        order_by: Optional ORDER BY clause (without the ORDER BY keywords)
        limit: Optional LIMIT for number of rows
        columns: Optional list of specific columns to retrieve
    
    Returns:
        List of dictionaries representing rows, or None if error occurs
    """
    try:
        # Get connection from lifespan context
        conn = ctx.request_context.lifespan_context["conn"]
        
        if conn is None:
            logger.error("Database connection is not available")
            return None
        
        # Validate table name
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = $1)",
            table_name
        )
        if not table_exists:
            logger.error(f"Table '{table_name}' does not exist")
            return None
        
        # Build query
        if columns:
            sanitized_columns = [f'"{col}"' for col in columns]
            columns_str = ", ".join(sanitized_columns)
            if table_name=='agenda':
                query = f'SELECT {columns_str} FROM "{table_name}"  as s1 left join "patients" as s2 on s1.patient_number=s2.patient_number left join appointment_types as s3 on s1.appointment_type=s3.appointment_number'
            else:
                query = f'SELECT {columns_str} FROM "{table_name}"'
        else:
            query = f'SELECT * FROM "{table_name}"'
        
        # Add WHERE clause if provided
        if where_clause:
            query += f" WHERE {where_clause}"
        
        # Add ORDER BY if provided
        if order_by:
            query += f" ORDER BY {order_by}"
        
        # Add LIMIT if provided
        if limit:
            query += f" LIMIT {limit}"
        
        # Execute query
        rows = await conn.fetch(query)
        result = [dict(row) for row in rows]
        
        logger.info(f"Successfully retrieved {len(result)} rows from {table_name}")
        return result
            
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


# Define tools for the MCP server: create appointment
@mcp.tool()
async def create_appointment(
    ctx: Context,
    patient_name: str,
    appointment_date: Optional[str] = None,
    appointment_type: str = "General Consultation",
    start_time: Optional[str] = None,
    duration: int = 30,
    patient_address: Optional[str] = None,
    patient_phone: Optional[str] = None
) -> Dict[str, Any] | None:
    """
    Create a new appointment and patient if needed.
    
    Args:
        patient_name: Name of the patient
        appointment_date: Date of appointment (YYYY-MM-DD)
        appointment_type: Type of appointment (e.g. 'General Consultation')
        start_time: Start time of appointment in HH:MM format
        duration: Duration of the appointment in minutes
        patient_address: Optional address of the patient
        patient_phone: Optional phone number
    
    Returns:
        Dictionary with appointment details or None if error occurs
    """
    try:
        logger.info("Attempting to create appointment")
        conn = ctx.request_context.lifespan_context["conn"]

        if conn is None:
            logger.error("Database connection is not available")
            return None

        async with conn.transaction():
            logger.info(f"Checking if patient '{patient_name}' exists...")
            patient = await conn.fetchrow(
                'SELECT patient_number FROM patients WHERE name = $1',
                patient_name
            )

            if not patient:
                logger.info(f"Patient '{patient_name}' not found. Creating new patient...")
                last_patient_number = await conn.fetchval(
                    'SELECT patient_number FROM patients order by patient_number desc limit 1'
                )
                if last_patient_number is None:
                    patient_number = "P001"
                else:
                    patient_number = f"P{int(last_patient_number[1:]) + 1:03d}"
                patient_number = await conn.fetchval(
                    'INSERT INTO patients (patient_number, name, address, phonenumber) VALUES ($1, $2, $3, $4) RETURNING patient_number',
                    patient_number, patient_name, patient_address, patient_phone
                )
                logger.info(f"Created new patient with number: {patient_number}")
                newpatient = True
            else:
                patient_number = patient['patient_number']
                logger.info(f"Found existing patient with number: {patient_number}")
                newpatient = False

            logger.info(f"Checking if appointment type '{appointment_type}' exists...")
            appointment_type_record = await conn.fetchrow(
                'SELECT appointment_number FROM appointment_types WHERE name = $1',
                appointment_type
            )

            if not appointment_type_record:
                logger.info(f"Appointment type '{appointment_type}' not found. Creating new type...")
                appointment_number = await conn.fetchval(
                    'INSERT INTO appointment_types (name) VALUES ($1) RETURNING appointment_number',
                    appointment_type
                )
                logger.info(f"Created new appointment type with appointment_number: {appointment_number}")
            else:
                appointment_number = appointment_type_record['appointment_number']
                logger.info(f"Found existing appointment type with appointment_number: {appointment_number}")

            


            logger.info("Formatting start and end times...")
            appointment_date = datetime.strptime(appointment_date, '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(start_time, '%H:%M').time()
            start_dt = datetime.combine(appointment_date, start_time_obj)
            end_dt = start_dt + timedelta(minutes=duration)

            logger.info("calculating id ...")
            id_max = await conn.fetchval('SELECT max(id) as max_id FROM agenda')
            id_record = id_max + 1 if id_max else 1
            logger.info(f"ID of new record: {id_record}")

            logger.info("Inserting appointment into agenda...")
            appointment = await conn.fetchrow(
                '''
                INSERT INTO agenda (id, patient_number, appointment_type, appointment_date, start_hour, end_hour)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
                ''',
                id_record, patient_number, appointment_number, appointment_date, start_dt.time(), end_dt.time()
            )

            logger.info("Appointment successfully created")
            return dict(appointment)

    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None


# Define tools for the MCP server: get number of rows in appointments table
@mcp.tool()
async def get_agenda_summary(ctx: Context) -> Dict[str, Any] | None:
    """
    Get a summary of the agenda system including appointment counts and averages.
    
    Returns:
        Dictionary with summary statistics or None if error occurs
    """
    try:
        conn = ctx.request_context.lifespan_context["conn"]
        
        if conn is None:
            logger.error("Database connection is not available")
            return None
        
        # Get total appointments
        total_appointments = await conn.fetchval('SELECT COUNT(*) FROM agenda')
        
        # Get total patients
        total_patients = await conn.fetchval('SELECT COUNT(*) FROM patients')
        
        # Get daily average (last 30 days)
        daily_avg = await conn.fetchval('''
            SELECT ROUND(AVG(count), 2) FROM (
                SELECT DATE(appointment_date), COUNT(*) as count 
                FROM agenda 
                WHERE appointment_date >= CURRENT_DATE - INTERVAL '30 days'
                GROUP BY DATE(appointment_date)
            ) as daily
        ''')
        
        # Get weekly average (last 12 weeks)
        weekly_avg = await conn.fetchval('''
            SELECT ROUND(AVG(count), 2) FROM (
                SELECT DATE_TRUNC('week', appointment_date), COUNT(*) as count 
                FROM agenda 
                WHERE appointment_date >= CURRENT_DATE - INTERVAL '12 weeks'
                GROUP BY DATE_TRUNC('week', appointment_date)
            ) as weekly
        ''')
        
        # Get monthly average (last 12 months)
        monthly_avg = await conn.fetchval('''
            SELECT ROUND(AVG(count), 2) FROM (
                SELECT DATE_TRUNC('month', appointment_date), COUNT(*) as count 
                FROM agenda 
                WHERE appointment_date >= CURRENT_DATE - INTERVAL '12 months'
                GROUP BY DATE_TRUNC('month', appointment_date)
            ) as monthly
        ''')
        
        logger.info("Successfully retrieved agenda summary")
        return {
            "total_appointments": total_appointments,
            "total_patients": total_patients,
            "daily_average": daily_avg or 0,
            "weekly_average": weekly_avg or 0,
            "monthly_average": monthly_avg or 0
        }
            
    except asyncpg.PostgresError as e:
        logger.error(f"PostgreSQL error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting agenda summary: {e}")
        return None

if __name__ == "__main__":
    # Initialize and run the server
    try:
        logger.info("Starting MCP server")
        mcp.run(transport='stdio')
    except Exception as e:
        logger.critical(f"Server startup failed: {e}", exc_info=True)
        sys.exit(1)