# Aqua Equity API Documentation

Base URL: `https://aqua-equity-api-java-production.up.railway.app`

---

## Authentication

### Login
`POST /api/auth/login`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

**Response:**
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "johndoe",
  "message": "Login successful"
}
```

---

## Users

### Get All Users
`GET /api/users`

No request body required.

---

### Get User by ID
`GET /api/users/{id}`

No request body required.

---

### Search User by Email or Username
`GET /api/users/search?email=user@example.com`
`GET /api/users/search?username=johndoe`

No request body required.

---

### Get Farms by User
`GET /api/users/{id}/farms`

No request body required.

---

### Create User
`POST /api/users`

**Request Body:**
```json
{
  "fristName": "John",
  "lastName": "Doe",
  "email": "user@example.com",
  "username": "johndoe",
  "password": "secret",
  "phoneNumber": "+1234567890"
}
```

---

### Update User (Partial)
`PATCH /api/users/{id}`

All fields are optional — only include the fields you want to update.

**Request Body:**
```json
{
  "fristName": "Jane",
  "lastName": "Doe",
  "email": "newemail@example.com",
  "username": "janedoe",
  "password": "newpassword",
  "phoneNumber": "+0987654321"
}
```

---

### Delete User
`DELETE /api/users/{id}`

No request body required. Returns `204 No Content` on success.

---

## Farms

### Get All Farms
`GET /api/farms`

No request body required.

---

### Get Farm by ID
`GET /api/farms/{id}`

No request body required.

---

### Get Farms by Region
`GET /api/farms/region/{regionId}`

No request body required.

---

### Get Farms by User
`GET /api/farms/user/{userId}`

No request body required.

---

### Create Farm
`POST /api/farms`

**Request Body:**
```json
{
  "farmName": "Green Acres",
  "hectares": 150.5,
  "quota": 200.0,
  "usedToday": 50.0,
  "userId": 1,
  "cropId": 2,
  "regionId": 3,
  "topLeftX": 41.123,
  "topLeftY": 21.456,
  "topRightX": 41.789,
  "topRightY": 21.456,
  "bottomLeftX": 41.123,
  "bottomLeftY": 21.012,
  "bottomRightX": 41.789,
  "bottomRightY": 21.012,
  "soilMoisture": 35.0,
  "stressLevel": 0.2,
  "uncertaintyLevel": 0.1
}
```

---

### Update Farm (Partial)
`PATCH /api/farms/{id}`

All fields are optional — only include the fields you want to update.

**Request Body:**
```json
{
  "farmName": "Updated Farm Name",
  "hectares": 200.0,
  "quota": 250.0,
  "usedToday": 75.0,
  "userId": 1,
  "cropId": 3,
  "regionId": 2,
  "topLeftX": 41.123,
  "topLeftY": 21.456,
  "topRightX": 41.789,
  "topRightY": 21.456,
  "bottomLeftX": 41.123,
  "bottomLeftY": 21.012,
  "bottomRightX": 41.789,
  "bottomRightY": 21.012,
  "soilMoisture": 40.0,
  "stressLevel": 0.3,
  "uncertaintyLevel": 0.15
}
```

---

### Delete Farm
`DELETE /api/farms/{id}`

No request body required. Returns `204 No Content` on success.

---

## Alerts

### Get All Alerts by User
`GET /api/alerts/user/{userId}`

No request body required.

---

### Create Alert
`POST /api/alerts`

**Request Body:**
```json
{
  "farmId": 1,
  "message": "Water usage exceeded threshold",
  "severity": "HIGH",
  "timeStamp": "2026-04-25T10:30:00",
  "waterAmount": 120.5
}
```

---

### Update Alert (Partial)
`PATCH /api/alerts/{id}`

All fields are optional — only include the fields you want to update.

**Request Body:**
```json
{
  "farmId": 1,
  "message": "Updated alert message",
  "severity": "LOW",
  "timeStamp": "2026-04-25T12:00:00",
  "waterAmount": 80.0
}
```

---

### Delete Alert
`DELETE /api/alerts/{id}`

No request body required. Returns `204 No Content` on success.

---

## Crops

### Create Crop
`POST /api/crops`

**Request Body:**
```json
{
  "cropName": "Wheat"
}
```

---

### Update Crop
`PATCH /api/crops/{id}`

**Request Body:**
```json
{
  "cropName": "Corn"
}
```

---

### Delete Crop
`DELETE /api/crops/{id}`

No request body required. Returns `204 No Content` on success.

---

## Regions

### Create Region
`POST /api/regions`

**Request Body:**
```json
{
  "regionName": "North Zone"
}
```

---

### Update Region
`PATCH /api/regions/{id}`

**Request Body:**
```json
{
  "regionName": "South Zone"
}
```

---

### Delete Region
`DELETE /api/regions/{id}`

No request body required. Returns `204 No Content` on success.

---

## Estimates

### Get All Estimates by User
`GET /api/estimates/user/{userId}`

No request body required.

---

### Create Estimate
`POST /api/estimates`

**Request Body:**
```json
{
  "farmId": 1,
  "estimateDate": "2026-04-25T00:00:00",
  "xPred": 0.45,
  "pPred": 0.02,
  "xUpd": 0.43,
  "pUpd": 0.01,
  "rainMm": 12.5,
  "et0Mm": 5.0,
  "irrigationMm": 20.0,
  "ndviMean": 0.65,
  "moistureMeanMm": 35.0,
  "updated": "2026-04-25T08:00:00",
  "stressLevel": 0.2
}
```

---

### Update Estimate (Partial)
`PATCH /api/estimates/{id}`

All fields are optional — only include the fields you want to update.

**Request Body:**
```json
{
  "farmId": 1,
  "estimateDate": "2026-04-26T00:00:00",
  "xPred": 0.50,
  "pPred": 0.03,
  "xUpd": 0.48,
  "pUpd": 0.02,
  "rainMm": 8.0,
  "et0Mm": 4.5,
  "irrigationMm": 15.0,
  "ndviMean": 0.70,
  "moistureMeanMm": 38.0,
  "updated": "2026-04-26T08:00:00",
  "stressLevel": 0.15
}
```

---

### Delete Estimate
`DELETE /api/estimates/{id}`

No request body required. Returns `204 No Content` on success.

---

## Irrigation Events

### Get All Irrigation Events by User
`GET /api/irrigation-events/user/{userId}`

No request body required.

---

### Create Irrigation Event
`POST /api/irrigation-events`

**Request Body:**
```json
{
  "farmId": 1,
  "waterAmount": 50.0,
  "timeStamp": "2026-04-25T06:00:00",
  "priority": "HIGH"
}
```

---

### Update Irrigation Event (Partial)
`PATCH /api/irrigation-events/{id}`

All fields are optional — only include the fields you want to update.

**Request Body:**
```json
{
  "farmId": 1,
  "waterAmount": 75.0,
  "timeStamp": "2026-04-25T08:00:00",
  "priority": "LOW"
}
```

---

### Delete Irrigation Event
`DELETE /api/irrigation-events/{id}`

No request body required. Returns `204 No Content` on success.

---

## Response Codes

| Code | Meaning |
|------|---------|
| `200 OK` | Request succeeded |
| `201 Created` | Resource created successfully |
| `204 No Content` | Delete succeeded |
| `404 Not Found` | Resource not found |
| `400 Bad Request` | Invalid request payload |
| `500 Internal Server Error` | Server error |