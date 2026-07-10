# ServiceOS — Staff App

Expo React Native app for field technicians (iOS + Android).

## Screens

| Screen | Description |
|---|---|
| Login | Phone + password → stores 5 keys in AsyncStorage |
| Home | Active job card, today's stats, upcoming jobs |
| Jobs | Status tabs (All/Assigned/In Progress/Done) |
| Job Detail | Status transitions, close modal, GPS tracking, Call customer |
| Chat | Room list → message thread |
| Earnings | Total earned, commission records |
| Profile | Performance signals, schedule edit, logout |

## Running

```bash
npm install
npx expo start            # → scan QR with Expo Go app
npx expo run:ios          # iOS simulator
npx expo run:android      # Android emulator
```

## Building for Distribution

```bash
npm install -g eas-cli
eas login
eas build --platform all --profile preview   # internal distribution
eas build --platform all --profile production
```

## Environment

```env
EXPO_PUBLIC_API_URL=https://api.serviceos.in
```

## Tests

```bash
python -m pytest tests/test_staff_app.py -v   # 51 tests
```

## Connecting to Backend

```bash
# 1. Copy env file
cp .env.example .env

# 2. For simulator/emulator — default works:
EXPO_PUBLIC_API_URL=http://localhost:8000

# 3. For physical device — use your computer's local IP:
#    Find it: ipconfig (Windows) | ifconfig (Mac) | ip addr (Linux)
EXPO_PUBLIC_API_URL=http://192.168.1.100:8000

# 4. Start backend, then app
uvicorn app.main:app --host 0.0.0.0 --port 8000   # --host 0.0.0.0 for device access
cd mobile/staff-app && npx expo start
```
