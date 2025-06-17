#!/usr/bin/env python3
"""
Migration script to hash all existing plain text passwords in the database.
This should be run once after implementing password hashing.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient
import bcrypt
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# MongoDB configuration
MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('DB_NAME', 'ai_clone')

def hash_password(password):
    """Hash a password using bcrypt"""
    # Convert string to bytes
    password_bytes = password.encode('utf-8')
    # Generate salt and hash
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    # Return as string for storage
    return hashed.decode('utf-8')

def is_password_hashed(password):
    """Check if a password is already hashed (bcrypt hashes start with $2b$)"""
    return password.startswith('$2b$') or password.startswith('$2a$')

def migrate_passwords():
    """Migrate all plain text passwords to hashed passwords"""
    try:
        # Connect to MongoDB
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,  # Less strict SSL cert verification
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )
        db = client[DB_NAME]
        users_collection = db['users']
        
        print("Starting password migration...")
        
        # Find all users with passwords
        users_with_passwords = users_collection.find({'password': {'$exists': True, '$ne': None, '$ne': ''}})
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for user in users_with_passwords:
            user_id = user.get('_id')
            email = user.get('email', 'unknown')
            current_password = user.get('password')
            
            print(f"Processing user: {email} ({user_id})")
            
            # Check if password is already hashed
            if is_password_hashed(current_password):
                print(f"  ✓ Password already hashed, skipping")
                skipped_count += 1
                continue
            
            try:
                # Hash the plain text password
                hashed_password = hash_password(current_password)
                
                # Update the user's password in the database
                result = users_collection.update_one(
                    {'_id': user_id},
                    {'$set': {'password': hashed_password}}
                )
                
                if result.modified_count > 0:
                    print(f"  ✓ Password migrated successfully")
                    migrated_count += 1
                else:
                    print(f"  ✗ Failed to update password")
                    error_count += 1
                    
            except Exception as e:
                print(f"  ✗ Error migrating password: {str(e)}")
                error_count += 1
        
        print(f"\nMigration completed:")
        print(f"  - Migrated: {migrated_count} passwords")
        print(f"  - Skipped (already hashed): {skipped_count} passwords")
        print(f"  - Errors: {error_count} passwords")
        
        if error_count > 0:
            print("\nSome passwords failed to migrate. Please check the errors above.")
            return False
        else:
            print("\n✓ All passwords successfully migrated!")
            return True
            
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return False
    finally:
        try:
            client.close()
        except:
            pass

def verify_migration():
    """Verify that all passwords in the database are properly hashed"""
    try:
        # Connect to MongoDB
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            retryWrites=True,
            w='majority'
        )
        db = client[DB_NAME]
        users_collection = db['users']
        
        print("Verifying password migration...")
        
        # Find all users with passwords
        users_with_passwords = users_collection.find({'password': {'$exists': True, '$ne': None, '$ne': ''}})
        
        unhashed_count = 0
        hashed_count = 0
        
        for user in users_with_passwords:
            email = user.get('email', 'unknown')
            current_password = user.get('password')
            
            if is_password_hashed(current_password):
                hashed_count += 1
            else:
                print(f"WARNING: User {email} still has unhashed password: {current_password}")
                unhashed_count += 1
                
        print(f"\nVerification results:")
        print(f"  - Properly hashed passwords: {hashed_count}")
        print(f"  - Unhashed passwords remaining: {unhashed_count}")
        
        if unhashed_count > 0:
            print("\n⚠️  Some passwords are still not hashed!")
            return False
        else:
            print("\n✓ All passwords are properly hashed!")
            return True
            
    except Exception as e:
        print(f"Error verifying migration: {str(e)}")
        return False
    finally:
        try:
            client.close()
        except:
            pass

if __name__ == '__main__':
    print("=== Password Migration Script ===")
    print("This script will hash all plain text passwords in your database.")
    print("Make sure you have a backup of your database before proceeding!")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed with the migration? (yes/no): ").lower().strip()
    if response not in ['yes', 'y']:
        print("Migration cancelled.")
        sys.exit(0)
    
    # Run migration
    success = migrate_passwords()
    
    if success:
        # Verify migration
        print("\nVerifying migration...")
        verify_migration()
        print("\n🎉 Password migration completed successfully!")
        print("Your database now stores passwords securely with bcrypt hashing.")
    else:
        print("\n❌ Migration failed. Please check the errors above.")
        sys.exit(1) 