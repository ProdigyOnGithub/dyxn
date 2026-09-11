"""
Authentication tests for the FastAPI server.
These tests verify that user registration and login endpoints work correctly,
including handling duplicate users and invalid credentials.
"""

def test_register_user_success(client):
    """
    Test that a new user can successfully register with a valid username and password.
    Should return a 201 Created status and a success message.
    """
    response = client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 201
    assert response.json() == {"message": "User created successfully"}

def test_register_user_duplicate(client):
    """
    Test that registering an existing user returns a 400 Bad Request.
    This ensures uniqueness constraint is enforced on usernames.
    """
    # Create the user first
    client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    
    # Try to create the same user again
    response = client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

def test_login_user_success(client):
    """
    Test that a registered user can log in and receive a valid JWT access token.
    The endpoint expects OAuth2 form data instead of JSON.
    """
    # First register a user
    client.post(
        "/register",
        json={"username": "testuser", "password": "testpassword"}
    )
    
    # Attempt to log in with the same credentials
    response = client.post(
        "/login",
        data={"username": "testuser", "password": "testpassword"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_user_invalid_credentials(client):
    """
    Test that logging in with incorrect credentials returns a 401 Unauthorized error.
    """
    response = client.post(
        "/login",
        data={"username": "nonexistent_user", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    assert "incorrect username or password" in response.json()["detail"].lower()
