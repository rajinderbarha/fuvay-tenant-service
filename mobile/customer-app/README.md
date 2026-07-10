# ServiceOS — Customer App

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
| Chat | Staff conversations (separate from AI) |
| AI Assistant | DeepSeek-powered chat — checks bookings, tracks jobs, estimates prices |
| Profile | Stats, menu, logout |

## AI Chat

The AI tab uses DeepSeek LLM via the ServiceOS backend. The API key is **never in the app** — it lives in the backend `.env`.

Customers can ask:
- "What are my recent bookings?"
- "Where is my technician?"
- "How much does AC service cost in Pune?"

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
python -m pytest tests/test_customer_app.py -v   # 55 tests
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

**AI Chat:** DeepSeek key is backend-only. Set `DEEPSEEK_API_KEY` in the backend `.env`.
The customer app never needs the key.
