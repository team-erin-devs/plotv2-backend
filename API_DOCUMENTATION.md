# Challenge Competition App - API Documentation

## Overview

This Django REST Framework API supports a university challenge competition app where users can complete weekly challenges by submitting proof files (images, videos, documents) and earn points for a leaderboard.

## Features

- **Challenge Management**: Create and manage weekly challenges with customizable file requirements
- **Proof Upload**: Users can upload files as proof of challenge completion
- **Review System**: Staff can review and approve/reject submitted proofs
- **Points System**: Automatic points calculation and leaderboard
- **File Validation**: Support for images, videos, and documents with size limits
- **User Profiles**: Extended user profiles with university information and stats

## Models

### Challenge
- `title`: Challenge name
- `description`: Detailed challenge description
- `points`: Points awarded for completion
- `week_number`: Week this challenge belongs to
- `is_active`: Whether challenge is currently available
- `allowed_file_types`: JSON array of allowed file extensions
- `max_file_size_mb`: Maximum file size in MB

### Proof
- `user`: User who submitted the proof
- `challenge`: Challenge this proof is for
- `file`: Uploaded proof file
- `description`: Optional description from user
- `status`: pending/approved/rejected
- `submitted_at`: Timestamp of submission
- `reviewed_at`: Timestamp of review
- `reviewed_by`: Staff member who reviewed
- `rejection_reason`: Reason for rejection (if applicable)
- `points_awarded`: Points actually awarded

### UserProfile
- `user`: One-to-one with Django User
- `total_points`: Calculated from approved proofs
- `university`: User's university
- `student_id`: Student identification number

## API Endpoints

### Authentication
All endpoints require authentication. The API supports:
- Session Authentication (for web interface)
- Basic Authentication (for API clients)

### Challenge Endpoints

#### `GET /api/challenges/`
List all active challenges with user's proof status.

**Response:**
```json
[
  {
    "id": 1,
    "title": "Morning Workout",
    "description": "Complete a 30-minute morning workout...",
    "points": 15,
    "week_number": 1,
    "is_active": true,
    "allowed_file_types": ["jpg", "jpeg", "png", "mp4", "mov"],
    "max_file_size_mb": 25,
    "created_at": "2024-01-15T10:00:00Z",
    "user_proof": null,
    "total_submissions": 5
  }
]
```

#### `GET /api/challenges/{id}/`
Get details of a specific challenge.

#### `GET /api/challenges/{id}/stats/`
Get statistics for a challenge (total submissions, approval rate, etc.).

### Proof Upload Endpoints

#### `POST /api/challenges/{challenge_id}/upload/`
Upload proof for a challenge.

**Request (multipart/form-data):**
- `file`: The proof file (required)
- `description`: Optional description (optional)

**Response:**
```json
{
  "id": 1,
  "user": {
    "id": 1,
    "username": "student1",
    "email": "student1@university.edu"
  },
  "challenge": {
    "id": 1,
    "title": "Morning Workout"
  },
  "file": "/media/proofs/1/uuid.jpg",
  "description": "My morning workout routine",
  "status": "pending",
  "submitted_at": "2024-01-15T10:30:00Z",
  "file_size_mb": 2.5,
  "file_extension": "jpg"
}
```

#### `GET /api/proofs/`
List all proofs submitted by the current user.

#### `GET /api/proofs/{id}/`
Get details of a specific proof.

#### `PATCH /api/proofs/{id}/` (Staff only)
Review a proof (approve/reject).

**Request:**
```json
{
  "status": "approved",
  "points_awarded": 15,
  "rejection_reason": ""
}
```

### Statistics and Leaderboard

#### `GET /api/leaderboard/`
Get the leaderboard with top users by points.

**Response:**
```json
[
  {
    "user": {
      "id": 1,
      "username": "student1",
      "email": "student1@university.edu"
    },
    "total_points": 45,
    "university": "Sample University",
    "student_id": "STU001"
  }
]
```

#### `GET /api/user/stats/`
Get current user's statistics.

**Response:**
```json
{
  "total_points": 45,
  "total_proofs": 3,
  "approved_proofs": 2,
  "pending_proofs": 1,
  "rejected_proofs": 0,
  "challenges_completed": 2,
  "leaderboard_position": 1
}
```

### Admin Endpoints

#### `GET /api/admin/proofs/`
List all proofs for review (staff only).

**Query Parameters:**
- `status`: Filter by status (pending, approved, rejected)

## File Upload Support

### Supported File Types
- **Images**: jpg, jpeg, png, gif
- **Videos**: mp4, mov, avi
- **Documents**: pdf

### File Size Limits
- Default: 50MB per file
- Configurable per challenge via `max_file_size_mb`

### File Storage
- Files are stored in `media/proofs/{challenge_id}/`
- Filenames are UUID-based for security
- File extensions are preserved

## Setup Instructions

1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Migrations:**
   ```bash
   python manage.py migrate
   ```

3. **Create Sample Data:**
   ```bash
   python manage.py create_sample_challenges
   ```

4. **Start Development Server:**
   ```bash
   python manage.py runserver
   ```

5. **Access Admin Interface:**
   - URL: `http://localhost:8000/admin/`
   - Username: `admin`
   - Password: `admin123`

## Example Usage with cURL

### Upload Proof
```bash
curl -X POST \
  -H "Authorization: Basic $(echo -n 'student1:student123' | base64)" \
  -F "file=@workout_photo.jpg" \
  -F "description=My morning workout routine" \
  http://localhost:8000/api/challenges/1/upload/
```

### Get User Stats
```bash
curl -X GET \
  -H "Authorization: Basic $(echo -n 'student1:student123' | base64)" \
  http://localhost:8000/api/user/stats/
```

### Review Proof (Staff)
```bash
curl -X PATCH \
  -H "Authorization: Basic $(echo -n 'admin:admin123' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "points_awarded": 15}' \
  http://localhost:8000/api/proofs/1/
```

## Flutter Integration

For Flutter frontend integration, you can use:

1. **HTTP Package**: For API calls
2. **Multipart Request**: For file uploads
3. **Shared Preferences**: For storing authentication tokens

Example Flutter code for uploading proof:
```dart
import 'package:http/http.dart' as http;
import 'package:http_parser/http_parser.dart';

Future<void> uploadProof(int challengeId, File file, String description) async {
  var request = http.MultipartRequest(
    'POST',
    Uri.parse('http://localhost:8000/api/challenges/$challengeId/upload/'),
  );
  
  request.files.add(await http.MultipartFile.fromPath(
    'file',
    file.path,
    contentType: MediaType('image', 'jpeg'),
  ));
  
  request.fields['description'] = description;
  request.headers['Authorization'] = 'Basic ${base64Encode(utf8.encode('username:password'))}';
  
  var response = await request.send();
  // Handle response
}
```

## Security Considerations

- File uploads are validated for type and size
- Unique filenames prevent conflicts
- User authentication required for all endpoints
- Staff-only endpoints for review functionality
- SQL injection protection via Django ORM
- CSRF protection for web interface

## Production Deployment

For production deployment:

1. Set `DEBUG = False` in settings
2. Configure proper database (PostgreSQL recommended)
3. Set up static file serving (nginx/Apache)
4. Configure media file serving
5. Use proper authentication (JWT tokens recommended)
6. Set up SSL/HTTPS
7. Configure proper CORS settings for Flutter app
