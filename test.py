import asyncio
import asyncpg
from types import SimpleNamespace
from postgres import create_appointment  # Adjust this import
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection parameters from environment variables
PG_HOST = os.getenv('PG_HOST', 'localhost')
PG_PORT = int(os.getenv('PG_PORT', '5432'))
PG_USER = os.getenv('PG_USER', 'postgres')
PG_PASSWORD = os.getenv('PG_PASSWORD', '')
PG_DATABASE = os.getenv('PG_DATABASE', 'postgres')


# Fake context to simulate ctx
class FakeContext:
    def __init__(self, conn):
        self.request_context = SimpleNamespace()
        self.request_context.lifespan_context = {"conn": conn}

async def test_create_appointment():
    # Connect to your test PostgreSQL database
    conn = await asyncpg.connect(host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            database=PG_DATABASE)

    ctx = FakeContext(conn)

    result = await create_appointment(
        ctx=ctx,
        patient_name="Jae Burli",
        appointment_date="2025-07-02",
        appointment_type="General Consultation",
        start_time="09:30",
        duration=30,
        patient_address="12 Main Street, NYC",
        patient_phone="555-0109431"
    )

    print("Result:", result)
    await conn.close()

# Run the test
asyncio.run(test_create_appointment())
