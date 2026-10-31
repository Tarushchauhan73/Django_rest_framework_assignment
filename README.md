
# Django REST Framework – User Management & Authentication API

A RESTful API built using **Django** and **Django REST Framework** for user management, JWT authentication, OTP verification, and password recovery. The API supports custom user profiles, user status management, project management, and email notifications.

## Features

- **Custom User Model:** Stores personal information, contact details, profile type, gender, nationality, blood group, and addresses.
- **User Management:** Create, list, retrieve, update, and soft-delete users.
- **Secure Passwords:** Passwords are hashed using Django's built-in password-hashing system.
- **JWT Authentication:** Secure login using access and refresh tokens.
- **Email Notifications:** Sends welcome emails when a user is created.
- **OTP Verification:** Sends time-limited OTPs through email.
- **Forgot Password:** Supports OTP-based password reset.
- **Input Validation:** Uses Django REST Framework serializers to validate request data.
- **Soft Delete:** Marks a user as `Inactive` instead of permanently deleting their database record.
- **Dynamic Profiles:** Supports standard and additional user roles, with protection for default roles.
- **Project Management:** Provides project CRUD operations and project file attachments.
- **Restore APIs:** Supports reactivating users and clients and restoring soft-deleted projects.

## Technology Stack

- Python
- Django
- Django REST Framework
- Simple JWT
- SQLite (default development database)
- SMTP / Gmail
- Pillow (for image uploads)

## Project Structure

```text
django_rest_framework_assignment/
├── config/
│   ├── settings.py
│   ├── urls.py
│   └── ...
├── users/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── emails_ytils.py
├── manage.py
├── requirements.txt
└── README.md
```

**Note:** The email utility filename above matches the name used in the current project. If your file is named `email_utils.py`, update the filename accordingly.

## Client Management

The Client API provides CRUD operations to manage client records, along with pagination and audit tracking.

### Features

- Create new client records.
- Retrieve client details.
- Update existing client information.
- Delete client records.
- Paginate client lists with two records per page.
- Track who created and last updated each client, along with timestamps.
- Protect client endpoints using JWT authentication.

### Client API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/clients/` | Get all clients with pagination |
| POST | `/api/clients/` | Create a new client |
| GET | `/api/clients/<id>/` | Retrieve a client by ID |
| PUT | `/api/clients/<id>/` | Update a client |
| PATCH | `/api/clients/<id>/` | Partially update a client |
| DELETE | `/api/clients/<id>/` | Delete a client |
| PATCH | `/api/clients/<id>/restore/` | Reactivate an inactive client |

### Pagination

The Client API returns two records per page.

```text
GET /api/clients/
GET /api/clients/?page=2
```

The paginated response includes `count`, `next`, `previous`, and `results`.

### Audit Tracking

Each client record tracks:

- `created_by` — user who created the record.
- `created_at` — record creation timestamp.
- `updated_by` — user who last updated the record.
- `updated_at` — most recent update timestamp.

### Authentication

Client endpoints require JWT authentication. In Postman, select **Authorization → Bearer Token** and provide a valid access token.

### Technologies

Python, Django, Django REST Framework, SQLite, and Simple JWT.

## Dynamic Profile / Role Management

The Profile API manages user roles dynamically. It supports creating roles and retrieving the available roles.

### Default Profiles

The five standard roles used by the project are:

1. Administrator
2. Standard
3. Developer
4. Client
5. Human Resource

Additional roles can also be created when required.

### Profile API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/profiles/` | List all profiles/roles |
| POST | `/api/profiles/` | Create a profile/role |
| GET | `/api/profiles/<id>/` | Retrieve a profile/role |
| PUT | `/api/profiles/<id>/` | Update a dynamic role |
| PATCH | `/api/profiles/<id>/` | Partially update a dynamic role |
| DELETE | `/api/profiles/<id>/` | Delete a dynamic role |

**Default-role protection:** The standard roles are protected from update and delete operations. Dynamic roles can be updated or deleted.

### Creating a Dynamic Profile

Example request:

**POST** `/api/profiles/`

```json
{
    "role": "Tester"
}
```

The API creates the new role if it does not already exist.

## User Management

The User API supports user creation, retrieval, updating, and soft deletion.

### Creating a User

The email field is required when creating a user. Other fields can be supplied according to the serializer and model validation rules.

If a password is not supplied, the API generates a default password from the part of the email address before `@`, followed by `@123`.

Example:

- Email: `test@yopmail.com`
- Generated default password: `test@123`

The generated password is stored using Django's password-hashing system. Users should change a default password after their first login.

## Project Management

The Project API provides CRUD operations for project records.

### Project API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projects/` | List all active projects |
| POST | `/api/projects/` | Create a project |
| GET | `/api/projects/<id>/` | Retrieve a project |
| PUT | `/api/projects/<id>/` | Update a project |
| PATCH | `/api/projects/<id>/` | Partially update a project |
| DELETE | `/api/projects/<id>/` | Soft-delete a project or delete a specified attachment |
| PATCH | `/api/projects/<id>/restore/` | Restore a soft-deleted project |

Project CRUD endpoints require authentication according to the configured permissions. The project restore endpoint is publicly accessible in the current implementation.

### Project Attachments

Project files can be uploaded when creating or updating a project using `multipart/form-data`.

To upload multiple files, send multiple file values using the same `attachments` field.

Example:

| Key | Type | Value |
|---|---|---|
| title | Text | System App |
| manager | Text | 2 |
| attachments | File | lecture3.py |

### Delete a Specific Attachment

A particular attachment can be deleted through the project detail endpoint by sending its attachment ID in the DELETE request body.

**DELETE** `/api/projects/<id>/`

```json
{
    "attachment_id": 9
}
```

If no attachment ID is supplied, the project DELETE operation performs the project's configured soft-delete behavior.

### Restore / Reactivate APIs

The following endpoints restore records that were soft-deleted or marked inactive:

| Method | Endpoint | Description |
|---|---|---|
| PATCH | `/api/users/<id>/restore/` | Reactivate an inactive user |
| PATCH | `/api/clients/<id>/restore/` | Reactivate an inactive client |
| PATCH | `/api/projects/<id>/restore/` | Restore a soft-deleted project |

The project restore endpoint is configured with `AllowAny` in the current implementation, so it does not require a JWT access token. The user and client restore endpoints follow their respective view permission settings.

## Installation and Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd django_rest_framework_assignment
```

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with your repository URL.

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install django djangorestframework djangorestframework-simplejwt Pillow
```

If a `requirements.txt` file is available, use:

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Configure your Gmail SMTP credentials in the terminal before running the server:

```bash
export EMAIL_HOST_USER='your_gmail@gmail.com'
export EMAIL_HOST_PASSWORD='your_google_app_password'
```

Use a Google App Password rather than your regular Gmail password. Enable 2-Step Verification if required.

**Security note:** Never commit email credentials, secret keys, or other sensitive information to GitHub. Use environment variables or a local `.env` file excluded through `.gitignore`.

### 5. Apply database migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create an administrator account (optional)

```bash
python manage.py createsuperuser
```

### 7. Run the development server

```bash
python manage.py runserver
```

The local API base URL is:

`http://127.0.0.1:8000/api/`

## API Endpoints

### User APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/users/` | Create a user |
| GET | `/api/users/` | List active users |
| GET | `/api/users/<id>/` | Retrieve a user |
| PUT | `/api/users/<id>/` | Update a user |
| PATCH | `/api/users/<id>/` | Partially update a user |
| DELETE | `/api/users/<id>/` | Soft-delete a user |
| PATCH | `/api/users/<id>/restore/` | Reactivate a user |

### Authentication APIs

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/login/` | Log in with email and password |
| POST | `/api/auth/token/refresh/` | Refresh an access token |
| POST | `/api/auth/send-otp/` | Send an OTP to email |
| POST | `/api/auth/verify-otp/` | Verify an OTP |
| POST | `/api/auth/forgot-password/` | Request a password-reset OTP |
| POST | `/api/auth/reset-password/` | Reset the password |

### Profile APIs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/profiles/` | List profiles |
| POST | `/api/profiles/` | Create a profile |
| GET | `/api/profiles/<id>/` | Retrieve a profile |
| PUT | `/api/profiles/<id>/` | Update a dynamic profile |
| PATCH | `/api/profiles/<id>/` | Partially update a dynamic profile |
| DELETE | `/api/profiles/<id>/` | Delete a dynamic profile |

### Client APIs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/clients/` | List clients |
| POST | `/api/clients/` | Create a client |
| GET | `/api/clients/<id>/` | Retrieve a client |
| PUT | `/api/clients/<id>/` | Update a client |
| PATCH | `/api/clients/<id>/` | Partially update a client |
| DELETE | `/api/clients/<id>/` | Delete a client |
| PATCH | `/api/clients/<id>/restore/` | Reactivate a client |

### Project APIs

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/projects/` | List projects |
| POST | `/api/projects/` | Create a project |
| GET | `/api/projects/<id>/` | Retrieve a project |
| PUT | `/api/projects/<id>/` | Update a project |
| PATCH | `/api/projects/<id>/` | Partially update a project |
| DELETE | `/api/projects/<id>/` | Soft-delete a project or delete an attachment |
| PATCH | `/api/projects/<id>/restore/` | Restore a project |

**Authentication:** Protected endpoints require a valid JWT access token. Login and OTP endpoints are intended to be accessible without an existing access token.

## Example API Requests

### 1. Create a User

**POST** `/api/users/`

```json
{
    "username": "tarush123",
    "first_name": "Tarush",
    "last_name": "Chauhan",
    "email": "user@example.com",
    "password": "StrongPassword123!",
    "profiles": "Developer",
    "date_of_birth": "2003-05-15",
    "gender": "Male",
    "nationality": "Indian",
    "blood_group": "O+",
    "phone": "9876543210",
    "permanent_address": "Ambala City, Haryana",
    "current_address": "Mohali, Punjab",
    "emergency_contact_name": "Emergency Contact",
    "emergency_contact_number": "9876501234",
    "emergency_contact_relationship": "Parent",
    "status": "Active"
}
```

Use values that match the choices defined in your `User` model. Add the `image` field if required by your serializer.

### 2. Log In

**POST** `/api/auth/login/`

```json
{
    "email": "user@example.com",
    "password": "StrongPassword123!"
}
```

A successful response returns the user's ID, email, access token, and refresh token.

### 3. Send an OTP

**POST** `/api/auth/send-otp/`

```json
{
    "email": "user@example.com"
}
```

The OTP is sent to the user's email address and expires after five minutes, according to the current view implementation.

### 4. Verify an OTP

**POST** `/api/auth/verify-otp/`

```json
{
    "email": "user@example.com",
    "otp": "123456"
}
```

Replace the sample OTP with the code received by email.

### 5. Request a Password Reset

**POST** `/api/auth/forgot-password/`

```json
{
    "email": "user@example.com"
}
```

### 6. Reset a Password

**POST** `/api/auth/reset-password/`

```json
{
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewStrongPassword123!"
}
```

Replace the sample email and OTP with valid values.

## Screenshots

<img width="1436" height="773" alt="Screenshot 2026-10-15 at 11 25 15 AM" src="https://github.com/user-attachments/assets/87b6be3d-168c-499e-9276-07b24667cf76" />

<img width="1440" height="773" alt="Screenshot 2026-10-15 at 11 25 30 AM" src="https://github.com/user-attachments/assets/f7865d1f-01ec-482d-adc6-e0635ba233a7" />

<img width="1440" height="775" alt="Screenshot 2026-10-15 at 11 25 45 AM" src="https://github.com/user-attachments/assets/d9d5f4a1-b170-495d-a2c8-ded731c7f3a5" />

<img width="428" height="192" alt="WhatsApp Image 2026-10-15 at 15 17 53" src="https://github.com/user-attachments/assets/6edec202-27b6-4953-bf31-dd7ae9601a7e" />

<img width="1440" height="775" alt="Screenshot 2026-10-15 at 3 18 50 PM" src="https://github.com/user-attachments/assets/bb8d137d-561c-47d8-90b6-09aa8f321bbc" />

<img width="1440" height="776" alt="Screenshot 2026-10-15 at 3 23 16 PM" src="https://github.com/user-attachments/assets/5faa0e4e-4740-4caa-8ee0-718041e1bee2" />

<img width="1365" height="731" alt="Screenshot 2026-10-15 at 3 44 29 PM" src="https://github.com/user-attachments/assets/24374e82-803a-4ec5-b3bf-562522aa889b" />

<img width="1362" height="672" alt="Screenshot 2026-10-15 at 3 44 46 PM" src="https://github.com/user-attachments/assets/1dbb83d5-8826-4245-9236-dc6aae383169" />

<img width="1341" height="748" alt="Screenshot 2026-10-15 at 3 59 26 PM" src="https://github.com/user-attachments/assets/c810eabd-24e4-43a2-ad71-bc10352bcf75" />

<img width="1399" height="891" alt="Screenshot 2026-10-15 at 4 30 59 PM" src="https://github.com/user-attachments/assets/5a848e61-7700-43b4-8342-706c1d865985" />

<img width="1400" height="900" alt="Screenshot 2026-10-15 at 5 47 23 PM" src="https://github.com/user-attachments/assets/100ba884-ae62-477b-9e50-56753f7a7bd9" />

<img width="1440" height="780" alt="Screenshot 2026-10-15 at 11 25 03 AM" src="https://github.com/user-attachments/assets/
511cf133-e052-41f8-837b-df4e4f92a44d" />

<img width="1440" height="900" alt="Screenshot 2026-10-31 at 8 36 44 PM" src="https://github.com/user-attachments/assets/6b155f1a-7d6d-4c94-86c8-4c8bd755c268" />
<img width="1440" height="900" alt="Screenshot 2026-10-31 at 8 29 21 PM" src="https://github.com/user-attachments/assets/8ed1317c-24bc-4734-ba4d-c9deb7f193bd" />
<img width="1440" height="900" alt="Screenshot 2026-10-31 at 8 28 16 PM" src="https://github.com/user-attachments/assets/e4c9a30e-3cf6-4721-bcc6-02b0d4f954bd" />
<img width="1440" height="900" alt="Screenshot 2026-10-31 at 8 26 15 PM" src="https://github.com/user-attachments/assets/a7e993e7-65be-4e7f-ab11-650a254906fc" />
<img width="1440" height="900" alt="image" src="https://github.com/user-attachments/assets/5df769b6-7dcb-408d-9114-b7a1aea5c965" />






![Screenshot 2026-10-26 at 9.42.33 AM](Screenshot%202026-10-26%20at%209.42.33%20AM.png)

## Testing the API

You can test endpoints using **Thunder Client** in Visual Studio Code or Postman.

For protected endpoints:

1. Log in to obtain an access token.
2. Open the request's **Auth** section or add an authorization header.
3. Select Bearer Token authentication.
4. Enter the access token.
5. Send the request.

Header format:

```text
Authorization: Bearer YOUR_ACCESS_TOKEN
```

## Email Configuration Troubleshooting

If an OTP or welcome email fails:

1. Confirm `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` are set in the same terminal session used to run Django.
2. Confirm the Gmail App Password is valid.
3. Check the SMTP host, port, and TLS settings in `config/settings.py`.
4. Run a test email from the Django shell and inspect the complete error.
5. Ensure the email utility functions handle SMTP failures appropriately.

Do not expose credentials in API responses or public repositories.

## Future Improvements

- Add automated tests for serializers, authentication, and OTP expiration.
- Add rate limiting to login and OTP endpoints.
- Store OTPs securely and limit repeated verification attempts.
- Add pagination and filtering for user lists.
- Use a production database and a production-grade email service.
- Configure HTTPS and secure deployment settings.

## Author

**Tarush Chauhan**

GitHub: [Tarushchauhan73](https://github.com/Tarushchauhan73)

## License

This project was developed for learning and assignment purposes. Add an appropriate open-source license if you intend to distribute it publicly.
