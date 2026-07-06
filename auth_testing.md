# Auth Testing Playbook

Accounts (seeded on startup): see /app/memory/test_credentials.md
- Teacher: teacher@jamacademy.com / Teacher@123
- Student: student@jamacademy.com / Student@123

API test:
```
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d '=' -f2)
curl -s -X POST "$API_URL/api/auth/login" -H "Content-Type: application/json" -d '{"email":"student@jamacademy.com","password":"Student@123"}'
# → {user, access_token}. Use Authorization: Bearer <access_token> for protected routes.
curl -s "$API_URL/api/auth/me" -H "Authorization: Bearer $TOKEN"
```
Frontend stores token in localStorage key `jam_token` and sends Bearer header via axios interceptor (/app/frontend/src/lib/api.js).
