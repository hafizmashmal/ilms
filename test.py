import mysql.connector
from mysql.connector import Error

def test_database_connection():
    try:
        # Attempt to connect using your provided credentials
        print("Attempting to connect to the database...")
        connection = mysql.connector.connect(
            host="193.203.166.222",
            port=3306,
            database="",
            user="",
            password="" 
        )

        # Check if the connection was successful
        if connection.is_connected():
            print("\n✅ Connected successfully!")
            
            # Optional: Get server info to verify
            db_Info = connection.get_server_info()
            print(f"Connected to MySQL Server version: {db_Info}")

    except Error as e:
        print("\n❌ Failed to connect.")
        print(f"Error details: {e}")
        
        # Specific troubleshooting for Hostinger
        if "2003" in str(e) or "Access denied" in str(e):
            print("\nTroubleshooting Tip: This usually means Hostinger is blocking the connection.")
            print("Make sure you have added your computer's CURRENT public IP address to the 'Remote MySQL' section in your Hostinger hPanel.")

    finally:
        # Always ensure the connection is closed after testing
        if 'connection' in locals() and connection.is_connected():
            connection.close()
            print("Database connection closed.")

if __name__ == "__main__":
    test_database_connection()
    
    # This line forces the terminal to stay open until you hit Enter
    input("\nPress Enter to exit...")