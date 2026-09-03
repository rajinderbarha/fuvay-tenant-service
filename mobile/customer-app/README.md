# Fuvay — Customer App

Expo React Native app for end customers (iOS + Android).

## Screens

| Screen | Description |
|---|---|
| Login | Phone OTP (2-step) or email fallback |
| Home | Active job banner, 6-service quick-book grid, recent bookings |
| Book Service | Service picker, date/time, price estimate, confirm |
| My Bookings | All/Pending/Confirmed/Cancelled tabs |
| Booking Detail | Cancel modal, Track Technician CTA, Leave Review CTA |
| Job Tracking | Progress steps, live staff GPS poll (30s interval) |
| Review | Star rating, quick tags, comment, success state |
| Chat | Staff conversations |
| Profile | Stats, menu, logout |

## Running

```bash
npm install
npx expo start            # scan QR with Expo Go
```

## Environment

```env
EXPO_PUBLIC_API_URL=https://api.serviceos.in
# No DEEPSEEK_API_KEY needed — it stays on the backend
```

## Building

```bash
npm install -g eas-cli
eas build --platform all --profile production
```

## Tests

```bash
npm test -- --runInBand
```

## Connecting to Backend

```bash
# 1. Copy env file
cp .env.example .env

# 2. For simulator/emulator — default works:
EXPO_PUBLIC_API_URL=http://localhost:8000

# 3. For physical device — use your computer's local IP:
EXPO_PUBLIC_API_URL=http://192.168.1.100:8000

# 4. Start backend with host 0.0.0.0 (required for device access)
uvicorn app.main:app --host 0.0.0.0 --port 8000
cd mobile/customer-app && npx expo start
```
